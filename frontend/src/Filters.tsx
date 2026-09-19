import type { ReactNode } from "react";

type Cat = { id: string; label: string };

export function FilterBar({
  search,
  onSearch,
  searchPlaceholder = "Что вы ищете?",
  categories,
  category,
  onCategory,
  sorts,
  sort,
  onSort,
  extras,
  priceMin,
  priceMax,
  onPriceMin,
  onPriceMax,
}: {
  search?: string;
  onSearch?: (v: string) => void;
  searchPlaceholder?: string;
  categories?: Cat[];
  category?: string;
  onCategory?: (v: string) => void;
  sorts?: Cat[];
  sort?: string;
  onSort?: (v: string) => void;
  extras?: ReactNode;
  priceMin?: string;
  priceMax?: string;
  onPriceMin?: (v: string) => void;
  onPriceMax?: (v: string) => void;
}) {
  return (
    <div className="filter-bar">
      {onSearch ? (
        <input
          className="filter-search"
          placeholder={searchPlaceholder}
          value={search || ""}
          onChange={(e) => onSearch(e.target.value)}
        />
      ) : null}
      {categories && onCategory ? (
        <div className="filter-row" role="tablist" aria-label="Категории">
          {categories.map((c) => (
            <button key={c.id} type="button" className={category === c.id ? "on" : ""} onClick={() => onCategory(c.id)}>
              {c.label}
            </button>
          ))}
        </div>
      ) : null}
      {sorts && onSort ? (
        <div className="filter-row quiet" role="tablist" aria-label="Сортировка">
          {sorts.map((c) => (
            <button key={c.id} type="button" className={sort === c.id ? "on" : ""} onClick={() => onSort(c.id)}>
              {c.label}
            </button>
          ))}
        </div>
      ) : null}
      {extras}
      {onPriceMin && onPriceMax ? (
        <div className="filter-price">
          <label>
            От ₽
            <input inputMode="decimal" placeholder="0" value={priceMin || ""} onChange={(e) => onPriceMin(e.target.value)} />
          </label>
          <label>
            До ₽
            <input inputMode="decimal" placeholder="любая" value={priceMax || ""} onChange={(e) => onPriceMax(e.target.value)} />
          </label>
        </div>
      ) : null}
    </div>
  );
}
