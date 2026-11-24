import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Modal from "./Modal";

describe("Modal", () => {
  it("показывает заголовок и содержимое", () => {
    render(
      <Modal title="поиск: фрида" onClose={() => {}}>
        <p>ничего не найдено</p>
      </Modal>,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName("поиск: фрида");
    expect(screen.getByText("ничего не найдено")).toBeInTheDocument();
  });

  it("закрывается по крестику", async () => {
    const onClose = vi.fn();
    render(
      <Modal title="окно" onClose={onClose}>
        <p>текст</p>
      </Modal>,
    );
    await userEvent.click(screen.getByRole("button", { name: "закрыть" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("закрывается по клику мимо окна", async () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal title="окно" onClose={onClose}>
        <p>текст</p>
      </Modal>,
    );
    await userEvent.click(container.firstElementChild as HTMLElement);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("не закрывается по клику внутри окна", async () => {
    const onClose = vi.fn();
    render(
      <Modal title="окно" onClose={onClose}>
        <p>текст внутри</p>
      </Modal>,
    );
    await userEvent.click(screen.getByText("текст внутри"));
    expect(onClose).not.toHaveBeenCalled();
  });
});
