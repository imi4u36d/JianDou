import { describe, expect, it } from "vitest";
import {
  formatDateTime,
  formatModelKind,
} from "@/admin/features/users/user-management-presenters";

describe("user management presenters", () => {
  it("maps model kinds and preserves unknown values", () => {
    expect(formatModelKind("TEXT")).toBe("文本");
    expect(formatModelKind(" image ")).toBe("图片");
    expect(formatModelKind("audio")).toBe("audio");
  });

  it("keeps missing and invalid dates readable", () => {
    expect(formatDateTime()).toBe("未记录");
    expect(formatDateTime("invalid-date")).toBe("invalid-date");
  });
});
