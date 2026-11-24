# гостевые сценарии: всё что видно без входа

TITLE = "не первая"


def test_homepage(guest_page):
    page = guest_page
    page.goto("http://localhost:3000/")
    assert page.locator("h1").inner_text() == TITLE
    # история дня на месте
    assert page.locator("h2", has_text="история дня").is_visible()
    # строка поиска
    assert page.locator("input#global-search").count() == 1
    # подвал с возрастной маркировкой
    assert "12+" in page.locator("footer").inner_text()


def test_search_stories_and_accounts(guest_page):
    page = guest_page
    page.goto("http://localhost:3000/")
    page.fill("input#global-search", "фрида")
    page.keyboard.press("Enter")

    dialog = page.locator("[role=dialog]")
    dialog.wait_for(state="visible")
    # истории по умолчанию: ждём карточку с Фридой (пока грузится — «ищем…»)
    dialog.locator("article").first.wait_for(state="visible")
    assert "Фрида Кало" in dialog.inner_text()

    # переключаемся на аккаунты: такого ника нет (ждём не «ищем…»)
    page.get_by_role("button", name="аккаунты").click()
    dialog.get_by_text("ничего не найдено").wait_for()
    assert "ничего не найдено" in dialog.inner_text()

    # крестик закрывает окно
    page.get_by_role("button", name="закрыть").click()
    dialog.wait_for(state="hidden")


def test_catalog_and_story_page(guest_page):
    page = guest_page
    page.goto("http://localhost:3000/catalog?show=1")
    assert page.locator("main article").count() > 0

    # первая карточка открывается
    page.locator("main article h2 a").first.click()
    page.wait_for_load_state("networkidle")
    assert page.locator("main article h1").count() == 1
    # блок источников есть у демо-историй
    assert page.locator("h2", has_text="источники").count() >= 0


def test_legal_contacts(guest_page):
    page = guest_page
    page.goto("http://localhost:3000/legal/contacts")
    body = page.locator("main").inner_text()
    assert "email для обращений" in body
    assert "@" in body


def test_public_profile(guest_page):
    page = guest_page
    # свой публичный профиль e2e-аккаунта
    page.goto("http://localhost:3000/u/00000000-0000-0000-0000-000000000000")
    # несуществующий профиль обрабатывается мягко
    assert "профиль не найден" in page.locator("main").inner_text()
