/**
 * Landing page (Milestone 1 scaffold).
 * The interactive form, analysis flow, dashboard, and history are built out
 * in Milestone 4. This establishes layout, copy, and the ethical-use notice.
 */
export default function LandingPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-10">
        <h1 className="text-3xl font-semibold tracking-tight">
          X Behavior Analyzer
        </h1>
        <p className="mt-3 text-gray-400">
          Enter a public X username to analyze its{" "}
          <span className="text-accent">observable posting patterns</span> —
          activity, content, sentiment, engagement, and automation-pattern
          signals.
        </p>
      </header>

      <section className="rounded-xl border border-base-600 bg-base-800 p-6">
        <form className="flex flex-col gap-3 sm:flex-row" action="#">
          <input
            name="username"
            placeholder="@username"
            aria-label="X username"
            className="flex-1 rounded-lg border border-base-600 bg-base-900 px-4 py-3 outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="rounded-lg bg-accent px-6 py-3 font-medium text-base-900 hover:bg-accent-muted"
          >
            Analyze Profile
          </button>
        </form>
        <p className="mt-3 text-sm text-gray-500">
          Interactive analysis is enabled in Milestone 4. The backend already
          runs in demo mode — try usernames like <code>protected_demo</code> or{" "}
          <code>empty_demo</code> against the API.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2">
        {[
          ["Posting activity", "Frequency, cadence, most active hours & days."],
          ["Content & topics", "Keywords, hashtags, domains, and topics."],
          ["Sentiment", "Positive / neutral / negative distribution & trend."],
          ["Automation signals", "Transparent 0–100 pattern score with reasons."],
        ].map(([title, body]) => (
          <div
            key={title}
            className="rounded-lg border border-base-700 bg-base-800 p-4"
          >
            <h3 className="font-medium text-accent">{title}</h3>
            <p className="mt-1 text-sm text-gray-400">{body}</p>
          </div>
        ))}
      </section>

      <section className="mt-10 rounded-lg border border-yellow-700/40 bg-yellow-900/10 p-5 text-sm text-yellow-200/90">
        <h2 className="font-semibold">Privacy & ethical-use notice</h2>
        <p className="mt-2">
          This system analyzes only publicly available information from the
          official X API. It reports <strong>observable posting patterns</strong>{" "}
          and does not determine personality, mental health, beliefs, criminality,
          political identity, or whether an account is truly automated. Pattern
          scores describe observable signals, not confirmed facts.
        </p>
      </section>
    </main>
  );
}
