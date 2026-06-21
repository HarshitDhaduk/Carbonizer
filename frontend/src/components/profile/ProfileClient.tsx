"use client";

import { LogOut } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { queries } from "@/lib/queries";
import { useLogoutWithConfirm } from "@/lib/use-logout-with-confirm";
import { AppPage } from "@/components/layout/AppPage";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { AccountCard } from "./AccountCard";
import { DataSourcesCard } from "./DataSourcesCard";
import { StartingProfileCard } from "./StartingProfileCard";
import { PrivacyCard } from "./PrivacyCard";

export function ProfileClient() {
  return (
    <AppPage title="Profile">
      <ProfileContent />
    </AppPage>
  );
}

function ProfileContent() {
  const { confirmOpen, setConfirmOpen, requestLogout, confirmLogout } =
    useLogoutWithConfirm();

  const me = useQuery(queries.me());
  const connections = useQuery(queries.connections());
  const profile = useQuery(queries.onboardingProfile());
  const questionnaire = useQuery(queries.onboardingQuestions());

  const isLoading =
    me.isPending ||
    connections.isPending ||
    profile.isPending ||
    questionnaire.isPending;
  const error =
    me.error ?? connections.error ?? profile.error ?? questionnaire.error;

  if (error)
    return (
      <p className="text-sm text-danger">Couldn&apos;t load your profile.</p>
    );
  if (
    isLoading ||
    !me.data ||
    !connections.data ||
    !profile.data ||
    !questionnaire.data
  )
    return <div className="skeleton h-64 rounded-card" />;

  return (
    <div className="space-y-4">
      <AccountCard user={me.data} />
      <DataSourcesCard connections={connections.data} />
      {profile.data.answers && (
        <StartingProfileCard
          questions={questionnaire.data.questions}
          answers={profile.data.answers}
        />
      )}
      <PrivacyCard />

      <Button variant="danger" className="w-full" onClick={requestLogout}>
        <LogOut size={16} aria-hidden /> Log out
      </Button>

      <ConfirmDialog
        open={confirmOpen}
        title="Log out of Carbonizer?"
        description="You'll need to sign in again to see your dashboard."
        confirmLabel="Log out"
        confirmVariant="danger"
        onConfirm={confirmLogout}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
