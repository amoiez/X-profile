"use client";

import { compactNumber, formatDateShort } from "@/lib/format";
import { EmptyState } from "@/components/ui";
import type { EngagementMetrics } from "@/lib/types";

export function TopPostsTable({ engagement }: { engagement: EngagementMetrics }) {
  if (!engagement.top_posts?.length)
    return <EmptyState message="No posts available to rank." />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-gray-400">
          <tr className="border-b border-base-700">
            <th className="py-2 pr-3">Post</th>
            <th className="px-2">Date</th>
            <th className="px-2 text-right">Likes</th>
            <th className="px-2 text-right">Reposts</th>
            <th className="px-2 text-right">Replies</th>
            <th className="pl-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {engagement.top_posts.map((p) => (
            <tr key={p.post_id} className="border-b border-base-800 align-top">
              <td className="max-w-xs py-2 pr-3 text-gray-200">
                <span className="line-clamp-2">{p.text || "(no text)"}</span>
              </td>
              <td className="px-2 text-gray-400">{formatDateShort(p.created_at)}</td>
              <td className="px-2 text-right text-gray-300">{compactNumber(p.likes)}</td>
              <td className="px-2 text-right text-gray-300">{compactNumber(p.reposts)}</td>
              <td className="px-2 text-right text-gray-300">{compactNumber(p.replies)}</td>
              <td className="pl-2 text-right font-medium text-gray-100">
                {compactNumber(p.engagement)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
