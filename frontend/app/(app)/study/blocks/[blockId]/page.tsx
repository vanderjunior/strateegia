import { StudyBlockDetailReadOnlyClient } from "@/components/workspace/StudyBlockDetailReadOnlyClient";

function safeDecodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export default async function StudyBlockDetailPage({
  params
}: {
  params: Promise<{ blockId: string }>;
}) {
  const { blockId } = await params;
  return <StudyBlockDetailReadOnlyClient blockId={safeDecodeRouteParam(blockId)} />;
}
