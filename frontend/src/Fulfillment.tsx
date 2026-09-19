import { Check, Loader } from "lucide-react";
import { Link } from "react-router-dom";
import { formatRub } from "./lib/format";

export type FulfillStage = "pay" | "issue" | "done" | "error";

type Props = {
  stage: FulfillStage;
  order?: any;
  productName: string;
  quantity: number;
  recipient: string;
  kind?: string;
  error?: string;
  onClose: () => void;
};

const STEPS: { key: FulfillStage; title: string }[] = [
  { key: "pay", title: "Оплата" },
  { key: "issue", title: "Выдача" },
  { key: "done", title: "Готово" },
];

function rank(stage: FulfillStage) {
  if (stage === "pay") return 0;
  if (stage === "issue") return 1;
  if (stage === "done") return 2;
  return -1;
}

export function FulfillmentOverlay({
  stage,
  order,
  productName,
  quantity,
  recipient,
  kind,
  error,
  onClose,
}: Props) {
  const handle = (recipient || "").replace(/^@/, "");
  const isStars = kind === "stars" || !kind;
  const issueText = isStars
    ? `Отправляем ${quantity} Stars${handle ? ` @${handle}` : ""}`
    : `Оформляем ${productName}${handle ? ` для @${handle}` : ""}`;
  const payText = "Списываем сумму с баланса";
  const current = rank(stage);

  return (
    <div className="ffill" role="dialog" aria-modal="true" aria-label="Выдача заказа">
      <div className="ffill-card">
        {stage !== "error" && stage !== "done" ? (
          <ol className="ffill-rail">
            {STEPS.map((s, i) => {
              const done = current > i;
              const on = current === i;
              return (
                <li key={s.key} className={`ffill-step ${done ? "is-done" : ""} ${on ? "is-on" : ""}`}>
                  <span className="ffill-dot">
                    {done ? <Check size={12} /> : on ? <Loader size={12} className="ffill-spin" /> : i + 1}
                  </span>
                  <span>{s.title}</span>
                </li>
              );
            })}
          </ol>
        ) : null}

        {stage === "pay" && (
          <div className="ffill-copy">
            <div className="ffill-orb" aria-hidden><i /></div>
            <h2 className="h2 display">Оплата</h2>
            <p className="muted">{payText}</p>
          </div>
        )}

        {stage === "issue" && (
          <div className="ffill-copy">
            <div className="ffill-orb issuing" aria-hidden><i /></div>
            <h2 className="h2 display">Выдача</h2>
            <p className="muted">{issueText}</p>
          </div>
        )}

        {stage === "done" && (
          <div className="ffill-copy ffill-done">
            <div className="success-mark ffill-check"><Check size={36} /></div>
            <h2 className="h1 display">Всё выдано</h2>
            <p className="muted">
              {isStars
                ? `${quantity} Stars уже у ${handle ? `@${handle}` : "получателя"}`
                : `${productName} оформлен`}
            </p>
            {order ? (
              <>
                <div className="ticket-line">#{order.public_id}</div>
                <div className="h2 num">{formatRub(order.total_price)}</div>
                <Link className="btn block" to={`/orders/${order.public_id}`} onClick={onClose}>
                  Смотреть заказ
                </Link>
                <button className="btn ghost block" type="button" onClick={onClose}>Готово</button>
              </>
            ) : (
              <button className="btn block" type="button" onClick={onClose}>Готово</button>
            )}
          </div>
        )}

        {stage === "error" && (
          <div className="ffill-copy">
            <h2 className="h2 display">Не выдалось</h2>
            <p className="err">{error || "Не удалось завершить заказ"}</p>
            <button className="btn block" type="button" onClick={onClose}>Закрыть</button>
          </div>
        )}
      </div>
    </div>
  );
}
