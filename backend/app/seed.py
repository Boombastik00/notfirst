import asyncio
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.models import Story, StorySource, StoryTag, Tag, TagGroup
from app.models.enums import PublicationStatus, SourceType, StoryType, VerificationStatus
from app.seed_data import STORIES, TAG_GROUPS, TAGS

# детерминированные даты чтобы сортировка по новизне была предсказуемой в тестах
BASE_DATE = datetime(2026, 1, 1, tzinfo=UTC)

# имена тегов для текстов-заглушек: контентом займётся редакция отдельно
TAG_NAME = {(t["group"], t["slug"]): t["name_ru"] for t in TAGS}


def _placeholder_texts(story: dict) -> tuple[str, str]:
    country = TAG_NAME[("countries", story["country"])]
    profession = TAG_NAME[("professions", story["profession"])]
    # формулировка без падежей: названия стран и профессий остаются как в словаре
    summary = f"история женщины (страна: {country}, профессия: «{profession}»)"
    obstacles = [TAG_NAME[("obstacles", o)] for o in story.get("obstacles", [])]
    if obstacles:
        summary += ", сомнения: " + ", ".join(f"«{o}»" for o in obstacles)
    return f"Заглушка: {summary}.", f"Текст истории появится позже, этим займётся редакция. Здесь будет {summary}."

SOURCE_TYPES = [
    SourceType.BOOK,
    SourceType.ARTICLE,
    SourceType.INTERVIEW,
    SourceType.DOCUMENT,
    SourceType.VIDEO,
    SourceType.ARCHIVE,
]


async def run(database_url: str | None = None) -> dict[str, int]:
    # в production демо-истории не льём никогда, словари наоборот нужны
    seed_demo_stories = get_settings().app_env != "production"

    engine = create_async_engine(database_url or get_settings().database_url)
    try:
        async with engine.begin() as conn:
            await _seed_groups(conn)
            tag_id = await _seed_tags(conn)
            if seed_demo_stories:
                await _seed_stories(conn, tag_id)
            else:
                await conn.execute(
                    sa.delete(Story).where(Story.slug.like("demo-%"))
                )

            groups = await conn.scalar(sa.select(sa.func.count()).select_from(TagGroup))
            tags = await conn.scalar(sa.select(sa.func.count()).select_from(Tag))
            stories = await conn.scalar(sa.select(sa.func.count()).select_from(Story))
            return {"groups": groups or 0, "tags": tags or 0, "stories": stories or 0}
    finally:
        await engine.dispose()


async def _seed_groups(conn: sa.Connection) -> None:
    for group in TAG_GROUPS:
        stmt = (
            pg_insert(TagGroup)
            .values(**group)
            .on_conflict_do_update(
                index_elements=[TagGroup.code],
                set_={"name_ru": group["name_ru"], "sort_order": group["sort_order"]},
            )
        )
        await conn.execute(stmt)


async def _seed_tags(conn: sa.Connection) -> dict[tuple[str, str], int]:
    # порядок в TAGS важен: родители идут раньше своих подтегов
    sort_counters: dict[str, int] = {}
    parent_ids: dict[tuple[str, str], int] = {}

    for tag in TAGS:
        group_code = tag["group"]
        sort_counters[group_code] = sort_counters.get(group_code, -1) + 1
        parent_slug = tag.get("parent")
        values = {
            "group_id": sa.select(TagGroup.id).where(TagGroup.code == group_code).scalar_subquery(),
            "parent_id": parent_ids[(group_code, parent_slug)] if parent_slug else None,
            "slug": tag["slug"],
            "name_ru": tag["name_ru"],
            "sort_order": sort_counters[group_code],
        }
        stmt = pg_insert(Tag).values(**values).on_conflict_do_update(
            index_elements=[Tag.group_id, Tag.slug],
            set_={
                "name_ru": values["name_ru"],
                "parent_id": values["parent_id"],
                # порядок тоже синхронизируем: перестановка в сиде должна доехать до живой базы
                "sort_order": values["sort_order"],
            },
        )
        await conn.execute(stmt)
        row = (
            await conn.execute(
                sa.select(Tag.id).where(
                    Tag.slug == tag["slug"],
                    Tag.group_id
                    == sa.select(TagGroup.id).where(TagGroup.code == group_code).scalar_subquery(),
                )
            )
        ).scalar_one()
        parent_ids[(group_code, tag["slug"])] = row

    return parent_ids


async def _seed_stories(conn: sa.Connection, tag_id: dict[tuple[str, str], int]) -> None:
    # сверка: убираем демо-истории которых больше нет в сиде
    keep_slugs = [s["slug"] for s in STORIES]
    await conn.execute(sa.delete(Story).where(Story.slug.like("demo-%"), Story.slug.not_in(keep_slugs)))

    for index, story in enumerate(STORIES):
        created_at = BASE_DATE + timedelta(days=index)
        published_at = (
            created_at + timedelta(days=1) if story.get("publication", "published") == "published" else None
        )
        short_description, full_text = _placeholder_texts(story)
        values = {
            "slug": story["slug"],
            "title": f"Заголовок {index + 1}",
            "woman_name": story["woman_name"],
            "short_description": short_description,
            "full_text": full_text,
            "story_type": StoryType(story["type"]),
            "verification_status": VerificationStatus(story.get("verification", "verified")),
            "publication_status": PublicationStatus(story.get("publication", "published")),
            "country_tag_id": tag_id[("countries", story["country"])],
            "profession_tag_id": tag_id[("professions", story["profession"])],
            "age_tag_id": tag_id[("age_categories", story["age"])],
            "is_anonymous": bool(story.get("is_anonymous", False)),
            "created_by": None,
            "created_at": created_at,
            "updated_at": created_at,
            "published_at": published_at,
        }
        upsert = (
            pg_insert(Story)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Story.slug],
                set_={key: value for key, value in values.items() if key != "slug"},
            )
            .returning(Story.id)
        )
        story_id = (await conn.execute(upsert)).scalar_one()

        # теги истории пересобираем с нуля
        await conn.execute(sa.delete(StoryTag).where(StoryTag.story_id == story_id))
        refs: set[tuple[str, str]] = set()
        for theme in story.get("themes", []):
            refs.add(("themes", theme))
        for obstacle in story.get("obstacles", []):
            refs.add(("obstacles", obstacle))
        for achievement in story.get("achievements", []):
            refs.add(("achievements", achievement))
        for field in story.get("fields", []):
            refs.add(("fields", field))
        for circumstance in story.get("life", []):
            refs.add(("life_circumstances", circumstance))
        for group_code, slug in sorted(refs):
            await conn.execute(
                pg_insert(StoryTag)
                .values(story_id=story_id, tag_id=tag_id[(group_code, slug)])
                .on_conflict_do_nothing()
            )

        await conn.execute(sa.delete(StorySource).where(StorySource.story_id == story_id))
        for source_index in range(story.get("sources", 0)):
            await conn.execute(
                sa.insert(StorySource).values(
                    story_id=story_id,
                    title=f"Источник {source_index + 1}",
                    url=f"https://example.com/source/{story['slug']}-{source_index + 1}",
                    source_type=SOURCE_TYPES[(index + source_index) % len(SOURCE_TYPES)],
                )
            )


if __name__ == "__main__":
    print("сид завершён:", asyncio.run(run()))
