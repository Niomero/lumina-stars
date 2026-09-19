import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "./api/client";
import { formatRub } from "./lib/format";
import { haptic } from "./lib/telegram";

function prizeLabel(g: any) {
  if (g.reward_type === "balance") return `${formatRub(g.prize?.amount)} на баланс`;
  return g.prize?.name || "Товар";
}

function useCountdown(iso?: string | null) {
  const [left, setLeft] = useState("");
  useEffect(() => {
    if (!iso) {
      setLeft("");
      return;
    }
    const tick = () => {
      const ms = new Date(iso).getTime() - Date.now();
      if (ms <= 0) {
        setLeft("00:00:00");
        return;
      }
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      const s = Math.floor((ms % 60000) / 1000);
      setLeft(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [iso]);
  return left;
}

export function GiveawaysPage() {
  const list = useQuery({ queryKey: ["giveaways"], queryFn: () => api("/giveaways") });
  return (
    <div className="grid">
      <h1 className="h1 display">Бонусы</h1>
      <p className="muted lead">Розыгрыши призов: баланс или цифровой товар. Один аккаунт — одно участие.</p>
      {(list.data?.items || []).map((g: any) => (
        <Link key={g.id} to={`/bonuses/${g.id}`} className="panel pad grid">
          <div className="between">
            <b className="display">{g.title}</b>
            <span className={`badge ${g.status === "active" ? "ok" : ""}`}>{g.status === "active" ? "Активен" : "Завершён"}</span>
          </div>
          <div className="muted">Приз: {prizeLabel(g)}</div>
          <div className="muted">Участников: {g.participants}{g.max_participants ? ` / ${g.max_participants}` : ""}</div>
        </Link>
      ))}
      {!list.isLoading && !(list.data?.items || []).length && <div className="empty">Сейчас розыгрышей нет</div>}
    </div>
  );
}

export function GiveawayPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const g = useQuery({ queryKey: ["giveaway", id], queryFn: () => api(`/giveaways/${id}`), refetchInterval: 15000 });
  const left = useCountdown(g.data?.finish_at);
  const join = useMutation({
    mutationFn: () => api(`/giveaways/${id}/join`, { method: "POST" }),
    onSuccess: () => {
      haptic("success");
      qc.invalidateQueries({ queryKey: ["giveaway", id] });
      qc.invalidateQueries({ queryKey: ["giveaways"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
  if (!g.data) return <div className="skeleton tall" />;
  const d = g.data;
  return (
    <div className="grid product-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}><ArrowLeft size={16} /> Назад</button>
      <div className="panel pad grid">
        <div className="tiny">Бонус</div>
        <h1 className="h1 display">{d.title}</h1>
        {d.description ? <p className="muted lead">{d.description}</p> : null}
        <div className="h2">Приз: {prizeLabel(d)}</div>
        <div className="muted">Участников: {d.participants}{d.max_participants ? ` / ${d.max_participants}` : ""}</div>
        {d.finish_at && d.status === "active" ? <div className="h2 num">{left || "—"}</div> : null}
        {d.status === "finished" && d.won ? <div className="badge ok">Вы выиграли</div> : null}
        {d.status === "finished" && d.won && d.reward_status === "completed" ? (
          <p className="muted">Ваш приз уже выдан.{d.prize_order ? " Код лежит в «Мои покупки»." : ""}</p>
        ) : null}
        {d.status === "finished" && d.won && d.reward_status === "reward_pending" ? (
          <p className="muted">Приз будет выдан после завершения обработки.</p>
        ) : null}
        {d.prize_code ? (
          <div className="panel pad grid">
            <div className="tiny">Код приза</div>
            <b className="mono h2">{d.prize_code}</b>
          </div>
        ) : null}
        {d.prize_order ? <Link className="btn ghost" to={`/purchases/${d.prize_order}`}>Открыть покупку</Link> : null}
        {d.status === "finished" && !d.won ? <div className="muted">Розыгрыш завершён</div> : null}
      </div>
      {join.error && <div className="err">{(join.error as ApiError).message}</div>}
      {d.status === "active" && (
        <button className="btn block" disabled={d.joined || join.isPending} onClick={() => join.mutate()}>
          {d.joined ? "Вы участвуете в розыгрыше" : "Участвовать"}
        </button>
      )}
    </div>
  );
}
