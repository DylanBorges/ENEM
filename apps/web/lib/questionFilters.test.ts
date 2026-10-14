import { describe, expect, it } from "vitest";
import { questionCatalogHref, questionDetailHref, questionFilterQuery, readQuestionFilters } from "./questionFilters";

describe("question navigation context", () => {
  it("restores filters and the catalog page after opening a question", () => {
    const original = readQuestionFilters("?year=2025&area=CN&subject=Qu%C3%ADmica&difficulty=media&page=3");
    const detail = questionDetailHref("item-42", original);
    const restored = readQuestionFilters(new URL(detail, "https://example.test").search);

    expect(questionCatalogHref(restored)).toBe("/questions?year=2025&area=CN&subject=Qu%C3%ADmica&difficulty=media&page=3");
    expect(questionFilterQuery(restored, false)).toBe("?year=2025&area=CN&subject=Qu%C3%ADmica&difficulty=media");
  });

  it("rejects invalid URL values before requesting the catalog", () => {
    expect(readQuestionFilters("?year=invalid&area=XX&difficulty=unknown&page=-2")).toEqual({
      year: "", area: "", subject: "", difficulty: "", page: 1,
    });
  });
});
