import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { formatRub, when } from "../lib/format";

type Me = { role: string };
const canWrite = (role: string) => ["ADMIN", "SUPERADMIN"].includes(role);

function Err({ e }: { e: unknown }) {
  if (!e) return null;
  return <div className="err">{(e as ApiError).message || "Ошибка"}</div>;
}

const empty = {
  title: "",
  description: "",
  reward_type: "balance",
  reward_amount: "500",
  reward_product_id: "",
  winner_count: "1",
  finish_type: "time",
  finish_at: "",
  max_participants: "100",
};

function GiveawayCard({ g, write }: { g: any; write: boolean }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const finish = useMutation({
    mutationFn: () => api(`/admin/giveaways/${g.id}/finish`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-giveaways"] }),
  });
  const cancel = useMutation({
    mutationFn: () => api(`/admin/giveaways/${g.id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-giveaways"] }),
  });
  const people = useQuery({
    queryKey: ["adm-gpart", g.id],
    enabled: open,
    queryFn: () => api(`/admin/giveaways/${g.id}/participants`),
  });
  const prize = g.reward_type === "balance" ? `${formatRub(g.prize?.amount)} на баланс` : (g.prize?.name || "Товар");
  return (
    <div className="panel pad grid">
      <div className="between">
        <div>
          <b>{g.title}</b>
          <div className="muted">Приз: {prize} · победителей {g.winner_count}</div>
        </div>
        <span className={`badge ${g.status === "active" ? "ok" : g.status === "cancelled" ? "bad" : ""}`}>
          {g.status === "active" ? "Активен" : g.status === "finished" ? "Завершён" : "Отменён"}
        </span>
      </div>
      <div className="muted">
        Участников: {g.participants}{g.max_participants ? ` / ${g.max_participants}` : ""}
        {g.finish_at ? ` · до ${when(g.finish_at)}` : ""}
      </div>
      {(g.winners || []).length > 0 && (
        <div className="grid">
          <div className="tiny">Победители</div>
          {g.winners.map((w: any) => (
            <div key={w.user_id} className="between">
              <span>{w.user?.username ? `@${w.user.username}` : w.user?.first_name || w.user_id}</span>
              <span className="muted">{w.reward_status}</span>
            </div>
          ))}
        </div>
      )}
      {write && g.status === "active" && (
        <div className="row">
          <button className="btn" disabled={finish.isPending} onClick={() => finish.mutate()}>Завершить</button>
          <button className="btn ghost" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Отменить</button>
        </div>
      )}
      <Err e={finish.error || cancel.error} />
      <button className="btn ghost sm" type="button" onClick={() => setOpen(!open)}>
        {open ? "Скрыть участников" : "Участники"}
      </button>
      {open && (people.data?.items || []).map((p: any) => (
        <div key={p.user_id} className="between">
          <span>{p.user?.username ? `@${p.user.username}` : p.user?.first_name || p.user_id}</span>
          <span className="muted">{when(p.joined_at)}</span>
        </div>
      ))}
      {open && !(people.data?.items || []).length && !people.isLoading && <div className="muted">Пока никто не участвует</div>}
    </div>
  );
}

export function GiveawayAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const write = canWrite(me.role);
  const [form, setForm] = useState(empty);
  const list = useQuery({ queryKey: ["adm-giveaways"], queryFn: () => api("/admin/giveaways") });
  const products = useQuery({ queryKey: ["adm-digital"], queryFn: () => api("/admin/digital") });
  const create = useMutation({
    mutationFn: () =>
      api("/admin/giveaways", {
        method: "POST",
        body: JSON.stringify({
          title: form.title,
          description: form.description,
          reward_type: form.reward_type,
          reward_amount: form.reward_type === "balance" ? form.reward_amount : null,
          reward_product_id: form.reward_type === "product" ? Number(form.reward_product_id) : null,
          winner_count: Number(form.winner_count) || 1,
          finish_type: form.finish_type,
          finish_at: form.finish_type === "time" && form.finish_at ? new Date(form.finish_at).toISOString() : null,
          max_participants: form.max_participants ? Number(form.max_participants) : null,
        }),
      }),
    onSuccess: () => {
      setForm(empty);
      qc.invalidateQueries({ queryKey: ["adm-giveaways"] });
    },
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Розыгрыши</h1>
      {write && (
        <div className="panel pad grid">
          <div className="tiny">Создать розыгрыш</div>
          <input placeholder="Название" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input placeholder="Описание" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <div className="chips">
            <button className={form.reward_type === "balance" ? "on" : ""} onClick={() => setForm({ ...form, reward_type: "balance" })}>Баланс</button>
            <button className={form.reward_type === "product" ? "on" : ""} onClick={() => setForm({ ...form, reward_type: "product" })}>Товар</button>
          </div>
          {form.reward_type === "balance" ? (
            <input inputMode="decimal" placeholder="Сумма ₽" value={form.reward_amount} onChange={(e) => setForm({ ...form, reward_amount: e.target.value })} />
          ) : (
            <select value={form.reward_product_id} onChange={(e) => setForm({ ...form, reward_product_id: e.target.value })}>
              <option value="">Выберите товар</option>
              {(products.data?.items || []).map((p: any) => (
                <option key={p.id} value={p.id}>{p.name} · {formatRub(p.price)}</option>
              ))}
            </select>
          )}
          <div className="chips">
            <button className={form.finish_type === "time" ? "on" : ""} onClick={() => setForm({ ...form, finish_type: "time" })}>По времени</button>
            <button className={form.finish_type === "count" ? "on" : ""} onClick={() => setForm({ ...form, finish_type: "count" })}>По числу участников</button>
          </div>
          {form.finish_type === "time" && (
            <label className="tiny">Окончание
              <input type="datetime-local" value={form.finish_at} onChange={(e) => setForm({ ...form, finish_at: e.target.value })} />
            </label>
          )}
          <div className="row">
            <label className="tiny" style={{ flex: 1 }}>Победителей
              <input inputMode="numeric" value={form.winner_count} onChange={(e) => setForm({ ...form, winner_count: e.target.value })} />
            </label>
            <label className="tiny" style={{ flex: 1 }}>Макс. участников
              <input inputMode="numeric" value={form.max_participants} onChange={(e) => setForm({ ...form, max_participants: e.target.value })} />
            </label>
          </div>
          <Err e={create.error} />
          <button className="btn block" disabled={!form.title.trim() || create.isPending} onClick={() => create.mutate()}>Запустить</button>
        </div>
      )}
      {(list.data?.items || []).map((g: any) => (
        <GiveawayCard key={g.id} g={g} write={write} />
      ))}
      {!list.isLoading && !(list.data?.items || []).length && <div className="empty">Розыгрышей нет</div>}
    </div>
  );
}
