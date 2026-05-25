import { MaterialDetailReadOnlyClient } from "@/components/workspace/MaterialDetailReadOnlyClient";

export default async function MaterialDetailPage({
  params
}: {
  params: Promise<{ materialId: string }>;
}) {
  const { materialId } = await params;
  return <MaterialDetailReadOnlyClient materialId={materialId} />;
}
