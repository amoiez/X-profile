import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WeeklyActivityChart } from "@/components/charts";
import { ErrorState } from "@/components/ErrorState";
import { Badge, Stat } from "@/components/ui";

describe("ErrorState", () => {
  it("renders a friendly hint for a known error code", () => {
    render(<ErrorState code="PROFILE_PROTECTED" />);
    expect(screen.getAllByText(/protected/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /new analysis/i })).toBeInTheDocument();
  });

  it("falls back to the generic hint for a null code", () => {
    render(<ErrorState code={null} message="boom" />);
    expect(screen.getByText(/could not be completed/i)).toBeInTheDocument();
  });
});

describe("ui primitives", () => {
  it("renders a Stat", () => {
    render(<Stat label="Posts" value={42} hint="per day" />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("per day")).toBeInTheDocument();
  });

  it("renders a Badge", () => {
    render(<Badge tone="positive">Live</Badge>);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});

describe("WeeklyActivityChart", () => {
  it("shows an empty state when all values are zero", () => {
    render(<WeeklyActivityChart data={[0, 0, 0, 0, 0, 0, 0]} />);
    expect(screen.getByText(/no weekly activity/i)).toBeInTheDocument();
  });
});
