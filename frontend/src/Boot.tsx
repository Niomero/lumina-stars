import { Send } from "lucide-react";

type BootInfo = {
  app_name?: string;
  demo_login_enabled?: boolean;
  bot_username?: string | null;
  app_env?: string;
};

export function Preloader({ label }: { label: string }) {
  return (
    <div className="boot-screen" role="status" aria-live="polite">
      <div className="boot-inner">
        <div className="boot-mark" aria-hidden>L</div>
        <div className="boot-title display">Lumina</div>
        <div className="boot-bar" aria-hidden><i /></div>
        <div className="boot-label">{label}</div>
      </div>
    </div>
  );
}

export function TelegramGate({
  info,
  allowDemo,
  error,
  onDemo,
}: {
  info: BootInfo | null;
  allowDemo: boolean;
  error?: string;
  onDemo: () => void;
}) {
  const bot = info?.bot_username?.replace(/^@/, "");
  const href = bot ? `https://t.me/${bot}?startapp` : undefined;
  return (
    <div className="boot-screen gate-screen">
      <div className="boot-inner gate-inner">
        <div className="boot-mark" aria-hidden>L</div>
        <p className="tiny">Telegram Mini App</p>
        <h1 className="h1 display">Откройте в Telegram</h1>
        <p className="muted gate-copy">
          Lumina работает только через Web App бота. Так мы подтверждаем аккаунт и выдаём Stars.
        </p>
        {href ? (
          <a className="btn block" href={href} rel="noreferrer">
            <Send size={16} /> Открыть в Telegram
          </a>
        ) : (
          <div className="panel pad gate-hint">
            Найдите бота Lumina в Telegram и нажмите <b>Открыть магазин</b>.
          </div>
        )}
        {error ? <div className="err">{error}</div> : null}
        {allowDemo ? (
          <button className="btn ghost block" type="button" onClick={onDemo}>
            Продолжить просмотр
          </button>
        ) : null}
      </div>
    </div>
  );
}
