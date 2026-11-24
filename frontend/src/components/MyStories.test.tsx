import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import MyStories from "./MyStories";

const items = [
  {
    slug: "story-abc",
    title: "моя история",
    short_description: "описание истории",
    story_type: "community_story",
    verification_status: "pending",
    publication_status: "draft",
    created_at: "2026-11-24T10:00:00Z",
    country: null,
    profession: null,
  },
  {
    slug: "official-def",
    title: "официальная",
    short_description: "описание официальной",
    story_type: "verified_biography",
    verification_status: "verified",
    publication_status: "published",
    created_at: "2026-11-23T10:00:00Z",
    country: null,
    profession: null,
  },
];

vi.stubGlobal(
  "fetch",
  vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ items }),
    } as Response),
  ),
);

describe("MyStories", () => {
  it("свёрнут по умолчанию и раскрывается с количеством", async () => {
    render(<MyStories />);
    const summary = screen.getByText("мои истории");
    await userEvent.click(summary);
    expect(await screen.findByText("моя история")).toBeInTheDocument();
    expect(screen.getByText(/мои истории \(2\)/)).toBeInTheDocument();
  });

  it("статусы человеческим языком", async () => {
    render(<MyStories />);
    await userEvent.click(screen.getByText("мои истории"));
    expect(await screen.findByText(/на модерации/)).toBeInTheDocument();
    expect(screen.getByText(/опубликована/)).toBeInTheDocument();
  });

  it("фильтр официальные оставляет только официальную", async () => {
    render(<MyStories />);
    await userEvent.click(screen.getByText("мои истории"));
    await screen.findByText("официальная");

    await userEvent.click(screen.getByRole("button", { name: "показать фильтры" }));
    await userEvent.click(screen.getByLabelText("официальные"));

    expect(screen.getByText("официальная")).toBeInTheDocument();
    expect(screen.queryByText("моя история")).not.toBeInTheDocument();
  });
});
