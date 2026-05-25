import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";

export default async function EditalDetailPage({
  params
}: {
  params: Promise<{ editalId: string }>;
}) {
  const { editalId } = await params;
  return <EditalDetailReadOnlyClient editalId={editalId} />;
}
