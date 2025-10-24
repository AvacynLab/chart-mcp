import { render, screen } from "@testing-library/react";
import NewsList from "./news-list";

describe("NewsList", () => {
  it("renders a fallback when no articles are present", () => {
    render(<NewsList symbol="NVDA" items={[]} />);

    expect(screen.getByTestId("finance-news-empty")).toBeInTheDocument();
  });

  it("renders list items with accessible links", () => {
    render(
      <NewsList
        symbol="BTCUSD"
        items={[
          {
            id: "1",
            title: "Bitcoin franchit un nouveau cap",
            url: "https://example.com/article",
            publishedAt: "2024-01-01T12:00:00Z",
          },
        ]}
      />,
    );

    const section = screen.getByRole("region", { name: /actualités btcusd/i });
    expect(section).toBeInTheDocument();
    const list = section.querySelector("ul");
    expect(list).not.toBeNull();
    expect(screen.getByRole("link", { name: /bitcoin franchit/i })).toHaveAttribute(
      "href",
      "https://example.com/article",
    );
  });

  it("handles malformed items", () => {
    render(
      <NewsList
        items={[
          { id: "broken", title: "", url: null, publishedAt: "not-a-date" },
          { id: "missing" } as never,
        ]}
      />,
    );

    expect(screen.getAllByText(/titre indisponible/i)).toHaveLength(2);
    expect(screen.getAllByText(/date inconnue/i)).not.toHaveLength(0);
  });
});
