# сценарии вошедшей создательницы: официальный цикл истории целиком

import secrets

from conftest import _db, _run

TITLE_PREFIX = "e2e история"


def test_staff_sees_header(authed_page):
    page = authed_page
    page.goto("http://localhost:3000/")
    nav = page.locator("header nav").inner_text()
    assert "профиль" in nav
    assert "модерация" in nav
    assert "истории" in nav
    assert "админка" in nav
    assert "выйти" in nav


def test_official_story_full_cycle(authed_page):
    page = authed_page
    title = f"{TITLE_PREFIX} {secrets.token_hex(4)}"

    # 1. пишем официальную историю с двумя источниками
    page.goto("http://localhost:3000/write")
    page.fill("input[placeholder='о ком эта история']", title)
    page.fill(
        "textarea",
        "длинный текст официальной истории который проходит порог в двести символов. "
        "мы пишем его с запасом чтобы валидация точно пропустила форму и e2e-тест "
        "смог дойти до конца сценария не отваливаясь на проверке длины",
    )
    page.fill("input[placeholder='название источника']", "первый источник")
    page.fill("input[placeholder='ссылка (необязательно)']", "https://example.com/a")
    page.get_by_role("button", name="+ источник").click()
    page.locator("input[placeholder='ещё один источник']").fill("второй источник")
    page.get_by_role("button", name="отправить").click()

    page.locator("p[role=status]").wait_for()
    assert "история отправлена на модерацию" in page.locator("p[role=status]").inner_text()

    # 2. находим её в очереди модерации и публикуем
    page.goto("http://localhost:3000/moderation")
    card = page.locator("article", has_text=title)
    card.wait_for()
    card.get_by_role("button", name="опубликовать").click()
    page.locator("p[role=status]").wait_for()
    assert "опубликована" in page.locator("p[role=status]").inner_text()

    # 3. история в каталоге
    page.goto("http://localhost:3000/catalog?show=1")
    assert page.locator("article", has_text=title).count() == 1

    # 4. слаг узнаём из базы для уборки
    async def fetch_slug():
        db = await _db()
        try:
            return await db.fetchval(
                "select slug from stories where title = $1", title
            )
        finally:
            await db.close()

    slug = _run(fetch_slug())

    # страница истории с подписью авторки
    page.goto(f"http://localhost:3000/stories/{slug}")
    author = page.locator("main", has_text="авторка истории")
    assert author.count() == 1
    assert "авторка истории" in page.locator("main").inner_text()

    # 5. в «моих историях» с фильтром официальные
    page.goto("http://localhost:3000/profile")
    page.get_by_text("мои истории").click()
    my_card = page.locator("article", has_text=title)
    my_card.wait_for(state="visible")
    page.get_by_role("button", name="показать фильтры").click()
    page.get_by_label("официальные").check()
    assert page.locator("article", has_text=title).count() == 1

    # 6. уборка: сносим историю из базы
    async def cleanup():
        db = await _db()
        try:
            await db.execute("delete from stories where slug = $1", slug)
        finally:
            await db.close()

    _run(cleanup())

    # после уборки в каталоге её нет
    page.goto("http://localhost:3000/catalog?show=1")
    assert page.locator("article", has_text=title).count() == 0
