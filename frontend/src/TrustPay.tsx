import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Copy, ExternalLink, Shield } from "lucide-react";
import { api, ApiError, getToken } from "./api/client";
import { formatRub, payStatusLabel, payStatusTone } from "./lib/format";
import { bootTelegram, getWebApp, haptic, openExternal } from "./lib/telegram";

type Pay = {
  public_id: string;
  amount: string;
  fee: string;
  total: string;
  status: string;
  card_masked: string;
  card_copy?: string;
  card_number?: string;
  card_holder?: string | null;
  yoomoney_url?: string;
  created_at?: string;
  expires_at?: string;
};

function Chip() {
  return (
    <svg className="tp-chip" viewBox="0 0 48 36" aria-hidden="true">
      <rect x="1.2" y="1.2" width="45.6" height="33.6" rx="6" fill="url(#tpChipFill)" stroke="currentColor" strokeWidth="1.4" />
      <path d="M1 18h46M18 1.2v33.6" stroke="currentColor" strokeWidth="1.15" opacity=".85" />
      <defs>
        <linearGradient id="tpChipFill" x1="0" y1="0" x2="48" y2="36">
          <stop stopColor="#d7e6ff" />
          <stop offset="1" stopColor="#7aa2e8" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function Waves() {
  return (
    <svg className="tp-waves" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7.2 8.2c2.4 2.2 2.4 5.4 0 7.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M11 5.2c3.8 3.4 3.8 10.2 0 13.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M14.8 2.4c5.2 4.6 5.2 14.6 0 19.2" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

async function copyText(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    const el = document.createElement("textarea");
    el.value = value;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  }
}

async function loadPay(id: string): Promise<Pay> {
  try {
    return await api<Pay>(`/trust-pay/payments/${id}`);
  } catch {
    const res = await fetch(`/api/v1/trust-pay/receipt/${id}`);
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.success === false) {
      throw new ApiError(body?.error?.code || "ERROR", body?.error?.message || "Платёж не найден", res.status);
    }
    return body.data as Pay;
  }
}

export function TrustPayPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);
  const pay = useQuery({
    queryKey: ["tp", id],
    queryFn: () => loadPay(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "processing" || s === "pending" ? 3000 : false;
    },
  });

  useEffect(() => {
    const tg = getWebApp() || bootTelegram();
    tg?.setHeaderColor?.("#071428");
    tg?.setBackgroundColor?.("#071428");
    tg?.BackButton?.show?.();
    const back = () => nav("/balance");
    tg?.BackButton?.onClick?.(back);
    const meta = document.querySelector('meta[name="theme-color"]');
    const prev = meta?.getAttribute("content") || "";
    meta?.setAttribute("content", "#071428");
    document.body.classList.add("trust-body");
    return () => {
      tg?.BackButton?.hide?.();
      tg?.BackButton?.offClick?.(back);
      meta?.setAttribute("content", prev || "#0b0a09");
      document.body.classList.remove("trust-body");
    };
  }, [nav]);

  const paid = useMutation({
    mutationFn: () => api<Pay>(`/trust-pay/payments/${id}/paid`, { method: "POST" }),
    onSuccess: (data) => {
      haptic("success");
      qc.setQueryData(["tp", id], data);
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["tp-list"] });
    },
  });

  const cardDigits = (pay.data?.card_copy || pay.data?.card_number || "").replace(/\s/g, "");
  const cardShown = pay.data?.card_copy || pay.data?.card_number || pay.data?.card_masked || "";

  const copy = async () => {
    if (!cardDigits) return;
    const ok = await copyText(cardDigits);
    if (ok) {
      setCopied(true);
      haptic("success");
      window.setTimeout(() => setCopied(false), 1800);
    } else haptic("error");
  };

  const data = pay.data;
  const status = data?.status || "pending";

  return (
    <div className="trust">
      <header className="tp-top">
        <button className="tp-back" type="button" onClick={() => nav("/balance")} aria-label="Назад">
          <ArrowLeft size={18} />
        </button>
        <div className="tp-mark" aria-hidden="true">
          <Shield size={16} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="tiny">TRUST PAY</div>
          <h1 className="tp-title">Пополнение баланса</h1>
        </div>
      </header>

      {pay.isLoading && <div className="skeleton tp-skel" />}
      {pay.error && (
        <div className="empty err">
          {(pay.error as ApiError).message || "Не удалось загрузить платёж"}
          <div>
            <Link to="/balance" className="btn ghost" style={{ marginTop: 12, display: "inline-flex" }}>
              К балансу
            </Link>
          </div>
        </div>
      )}

      {data && (
        <>
          <div className="tp-idrow">
            <div className="tp-id">Оплата платежа {data.public_id}</div>
            <span className={`badge ${payStatusTone(status)}`}>{payStatusLabel(status)}</span>
          </div>

          <section className="tp-sums">
            <div className="tp-row">
              <span>К пополнению</span>
              <b className="num">{formatRub(data.amount)}</b>
            </div>
            <div className="tp-row">
              <span>Комиссия 3%</span>
              <b className="num">{formatRub(data.fee)}</b>
            </div>
            <div className="tp-row tp-total">
              <span>Необходимо перевести</span>
              <strong className="num">{formatRub(data.total)}</strong>
            </div>
          </section>

          {status !== "paid" && (
            <>
              <section className="tp-card" aria-label="Реквизиты получателя">
                <div className="tp-card-face">
                  <div className="tp-card-top">
                    <span>Перевод по номеру карты</span>
                    <Waves />
                  </div>
                  <div className="tp-pan">
                    <Chip />
                    <b>{cardShown}</b>
                  </div>
                  {data.card_holder && <div className="tp-holder">{data.card_holder}</div>}
                  <div className="tp-card-meta">Банковский перевод · RUB</div>
                </div>
                <button className="btn block tp-copy" type="button" onClick={copy}>
                  {copied ? (
                    <>
                      <Check size={16} /> Номер карты скопирован
                    </>
                  ) : (
                    <>
                      <Copy size={16} /> Скопировать номер
                    </>
                  )}
                </button>
              </section>

              {data.yoomoney_url && (
                <button
                  className="btn ghost block tp-yo"
                  type="button"
                  onClick={() => openExternal(data.yoomoney_url!)}
                >
                  <ExternalLink size={16} /> Открыть ЮMoney на {formatRub(data.total)}
                </button>
              )}
            </>
          )}

          {status === "pending" && (
            <>
              <ol className="tp-steps">
                <li>Скопируйте номер карты.</li>
                <li>Откройте приложение своего банка.</li>
                <li>Переведите {formatRub(data.total)} на указанную карту.</li>
                <li>После перевода вернитесь сюда.</li>
                <li>Нажмите «Я оплатил».</li>
              </ol>
              {paid.error && <div className="err">{(paid.error as ApiError).message}</div>}
              {!getToken() && (
                <p className="muted">Чтобы подтвердить перевод, откройте страницу кнопкой «Перейти к оплате» в боте.</p>
              )}
              <div className="tp-foot">
                <button className="btn block" disabled={paid.isPending || !getToken()} onClick={() => paid.mutate()}>
                  {paid.isPending ? "Проверяем платёж…" : "Я оплатил"}
                </button>
              </div>
            </>
          )}

          {status === "processing" && (
            <div className="tp-state">
              <div className="tp-pulse" aria-hidden="true" />
              <div className="tiny">Статус</div>
              <h2 className="h2">Платёж отправлен на проверку</h2>
              <p className="muted">Ожидает перевода. Баланс пополнится после подтверждения.</p>
            </div>
          )}

          {status === "paid" && (
            <div className="tp-state">
              <div className="success-mark">
                <Check size={32} />
              </div>
              <h2 className="h2">Оплата подтверждена</h2>
              <p>Баланс пополнен на {formatRub(data.amount)}</p>
              <Link className="btn block" to="/balance">
                Вернуться в магазин
              </Link>
            </div>
          )}

          {["failed", "cancelled", "expired"].includes(status) && (
            <div className="tp-state">
              <h2 className="h2">{payStatusLabel(status)}</h2>
              <p className="muted">Создайте новый платёж — сначала укажите сумму.</p>
              <Link className="btn block" to="/balance">
                К балансу
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
