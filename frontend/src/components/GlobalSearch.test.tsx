import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GlobalSearch from "./GlobalSearch";

const storiesResp = {
  items: [
    {
      slug: "demo-frida-kahlo",
      title: "Заголовок 5",
      woman_name: "Фрида Кало",
      short_description: "описание",
      is_anonymous: false,
      country: "Мексика",
      profession: "Культура и искусство",
    },
  ],
};

const accountsResp = [
  {
    id: "11111111-2222-3333-4444-555555555555",
    display_name: "понедельник",
    badges: [{ code: "creator", label: "создательница" }],
  },
];

// подменяем fetch: истории и аккаунты
vi.stubGlobal(
  "fetch",
  vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith("/api/v1/stories")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(storiesResp),
      } as Response);
    }
    if (url.startsWith("/api/v1/u/search")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(accountsResp),
      } as Response);
    }
    return Promise.reject(new Error(`неожиданный запрос ${url}`));
  }),
);

describe("GlobalSearch", () => {
  it("кнопка ищать недоступна пока меньше двух символов", () => {
    render(<GlobalSearch />);
    const input = screen.getByRole("searchbox");
    expect(screen.getByRole("button", { name: "искать" })).toBeDisabled();
  });

  it("по энтеру открывает окно с историями по умолчанию", async () => {
    render(<GlobalSearch />);
    const input = screen.getByRole("searchbox");
    await userEvent.type(input, "фрида{Enter}");

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAccessibleName("поиск: фрида");
    expect(screen.getByText("Заголовок 5")).toBeInTheDocument();
    // вкладка историй активна по умолчанию
    expect(screen.getByRole("button", { name: "истории" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("переключается на аккаунты и показывает найденных", async () => {
    render(<GlobalSearch />);
    await userEvent.type(screen.getByRole("searchbox"), "понедельник{Enter}");
    await screen.findByRole("dialog");

    await userEvent.click(screen.getByRole("button", { name: "аккаунты" }));
    expect(await screen.findByText("понедельник")).toBeInTheDocument();
    expect(screen.getByText("создательница")).toBeInTheDocument();
  });

  it("крестик закрывает окно", async () => {
    render(<GlobalSearch />);
    await userEvent.type(screen.getByRole("searchbox"), "фрида{Enter}");
    await screen.findByRole("dialog");

    await userEvent.click(screen.getByRole("button", { name: "закрыть" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
