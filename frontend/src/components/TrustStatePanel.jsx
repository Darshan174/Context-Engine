import { Link } from "react-router-dom";

const REVIEW_STYLE = {
  approved: "bg-emerald-100 text-emerald-700",
  needs_review: "bg-amber-100 text-amber-700",
  superseded: "bg-slate-100 text-slate-600",
  rejected: "bg-red-100 text-red-700",
};

const REVIEW_LABEL = {
  approved: "Approved",
  needs_review: "Needs review",
  superseded: "Superseded",
  rejected: "Rejected",
};

export default function TrustStatePanel({
  reviewStatus,
  reviewSummary,
  temporalState,
  reviewItemId,
  compact = false,
  className = "",
}) {
  const normalizedStatus = normalizeValue(reviewStatus);
  const normalizedTemporal = normalizeValue(temporalState);
  const showHistorical =
    normalizedTemporal === "historical" ||
    normalizedTemporal === "superseded" ||
    normalizedStatus === "superseded";

  if (!normalizedStatus && !showHistorical) {
    return null;
  }

  const showReviewLink =
    normalizedStatus === "needs_review" ||
    normalizedStatus === "superseded" ||
    normalizedStatus === "rejected";

  return (
    <div className={`${compact ? "space-y-2" : "space-y-2.5"} ${className}`.trim()}>
      <div className="flex flex-wrap items-center gap-2">
        {normalizedStatus && (
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
              REVIEW_STYLE[normalizedStatus] ?? "bg-slate-100 text-slate-600"
            }`}
          >
            {REVIEW_LABEL[normalizedStatus] ?? normalizedStatus.replaceAll("_", " ")}
          </span>
        )}
        {showHistorical && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600">
            Historical context
          </span>
        )}
        {showReviewLink && (
          <Link
            to={reviewItemId ? `/app/review/${reviewItemId}` : "/app/review"}
            className="text-[11px] font-medium text-brand-700 hover:text-brand-800"
          >
            {reviewItemId ? "Open review item" : "Open review queue"}
          </Link>
        )}
      </div>
      {reviewSummary && !compact && (
        <p className="text-xs text-gray-500">{reviewSummary}</p>
      )}
    </div>
  );
}

function normalizeValue(value) {
  return typeof value === "string" && value.trim() ? value.trim().toLowerCase() : null;
}
