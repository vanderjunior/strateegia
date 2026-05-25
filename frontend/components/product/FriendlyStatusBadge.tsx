import type { Audience, CapabilityStatus } from "@/lib/api/types";
import { statusToneBadgeClass } from "@/lib/adapters/capabilities";
import { Badge } from "@/components/ui/badge";
import { getUserFacingStatus } from "@/lib/product/product-language";

export function FriendlyStatusBadge({
  status,
  audience = "student"
}: {
  status: CapabilityStatus;
  audience?: Audience;
}) {
  const friendly = getUserFacingStatus(status, audience);

  return <Badge className={statusToneBadgeClass(friendly.tone)}>{friendly.label}</Badge>;
}

