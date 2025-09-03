#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Text Replacer (GUI) — Cyrillic-safe / expand-rect first / legacy-compatible
- Толерантный поиск (NBSP/типографские кавычки)
- Сначала расширение прямоугольника под исходный кегль, затем (если нужно) уменьшение
- Совместимость: fontname (новые версии) или fontfile (старые версии)
"""
from __future__ import annotations
import os
import fitz  # PyMuPDF
from tkinter import Tk, messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename, askopenfilename as askfont

# --- Что меняем ---
REPLACEMENTS = [
    ('ТОО "MOST Project"', 'ТОО "MOST Architects"'),
    ('ТОО «MOST Project»', 'ТОО «MOST Architects»'),
    ('ГСЛ №007748',        'ГСЛ № 18014212'),
    ('ГСЛ № 007748',       'ГСЛ № 18014212'),
]

# --- Кандидаты шрифтов (Arial покрывает кириллицу и знак №) ---
CANDIDATE_FONTS = [
    r"C:\\Users\\user\\Downloads\\GOST Common (1)\\gost_common.ttf",
    r"C:\Windows\Fonts\Arial.ttf",
    r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    r"/Library/Fonts/Arial Unicode.ttf",
]

SPACE_CHARS = [" ", "\u00A0", "\u2007", "\u2009"]
QUOTE_VARIANTS = [('"','"'), ('«','»'), ('“','”'), ('„','“')]

# ---------------------- Font selection & kwargs ----------------------
def pick_cyrillic_font_path() -> str:
    font_path = r"C:\\Users\\user\\Downloads\\GOST Common (1)\\gost_common.ttf"
    
    if os.path.isfile(font_path):
        return font_path
    else:
        # Если файл не найден, выдаём ошибку.
        # В этом случае пользователю придётся указать путь вручную
        raise FileNotFoundError(f"Font file not found at: {font_path}")
def get_font_kwargs(doc, font_path: str) -> dict:
    """
    Возвращает kwargs для insert_textbox:
      - новые версии: {'fontname': 'F0'}  (предварительно встроенный шрифт)
      - старые версии: {'fontfile': font_path}
    """
    if hasattr(doc, "insert_font"):
        for kw in ("file", "fontfile", "filename", "fname"):
            try:
                internal = doc.insert_font(**{kw: font_path})
                return {"fontname": internal}
            except TypeError:
                continue
        try:
            internal = doc.insert_font(font_path)  # позиционно
            return {"fontname": internal}
        except Exception:
            pass
    return {"fontfile": font_path}  # фолбэк для старых сборок

# ---------------------- Text geometry helpers ----------------------
def collect_spans(page: fitz.Page):
    spans = []
    pd = page.get_text("dict")
    for block in pd.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = span.get("bbox")
                if bbox:
                    spans.append((fitz.Rect(bbox), float(span.get("size", 0.0))))
    return spans

def rect_overlap(a: fitz.Rect, b: fitz.Rect) -> float:
    x0=max(a.x0,b.x0); y0=max(a.y0,b.y0)
    x1=min(a.x1,b.x1); y1=min(a.y1,b.y1)
    return 0.0 if (x1<=x0 or y1<=y0) else (x1-x0)*(y1-y0)

def dominant_fontsize(spans, target: fitz.Rect, min_size=5.5) -> float:
    best_ov, best_size = 0.0, 0.0
    for r, sz in spans:
        ov = rect_overlap(r, target)
        if ov > best_ov:
            best_ov, best_size = ov, sz
    return best_size if best_size > 0 else max(min_size, target.height * 0.9)

# ---------------------- Search (tolerant to NBSP / quotes) ----------------------
def phrase_variants(s: str):
    out = {s}
    # пробелы
    for sp in SPACE_CHARS:
        out.add(s.replace(" ", sp))
    # № с/без пробела
    out.add(s.replace("№ ", "№"))
    out.add(s.replace("№", "№ "))
    # парные кавычки (без тотальной перезатиралки)
    if '"' in s:
        parts = s.split('"')
        if len(parts) >= 3:
            l, mid, rtail = parts[0], parts[1], '"'.join(parts[2:])
            for lq, rq in QUOTE_VARIANTS:
                out.add(l + lq + mid + rq + rtail)
    if "«" in s and "»" in s:
        l = s.split("«", 1)[0]
        rest = s.split("«", 1)[1]
        if "»" in rest:
            mid, rtail = rest.split("»", 1)
            for lq, rq in QUOTE_VARIANTS:
                out.add(l + lq + mid + rq + rtail)
    return list(out)

def search_phrase_rects(page: fitz.Page, text: str):
    try:
        flags = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_LIGATURES
    except AttributeError:
        flags = 0
    rects = []
    for patt in phrase_variants(text):
        quads = page.search_for(patt, quads=True, flags=flags)
        if quads:
            rects.extend([fitz.Rect(q.rect) for q in quads])
    return rects

# ---------------------- Expand‑rect, then shrink font ----------------------
def try_fit_by_expanding_rect(page, rect, text, fontsize, font_kwargs,
                              max_expand=80, step=2, align=0):
    """
    Пытается уместить text в rect с фиксированным fontsize,
    расширяя rect симметрично влево/вправо до max_expand pt.
    Возвращает (True, new_rect) если влезло, иначе (False, base_rect).
    """
    pad = 0.5
    base = fitz.Rect(rect.x0 + pad, rect.y0 + pad, rect.x1 - pad, rect.y1 - pad)
    # быстрый тест
    y = page.insert_textbox(base, text, fontsize=fontsize, align=align, render_mode=3, **font_kwargs)
    if y > 0:
        return True, base

    dx = 0
    page_rect = page.rect
    while dx <= max_expand:
        dx += step
        new_rect = fitz.Rect(base.x0 - dx, base.y0, base.x1 + dx, base.y1)
        # не вылезаем за границы страницы
        if new_rect.x0 < page_rect.x0 + 1: new_rect.x0 = page_rect.x0 + 1
        if new_rect.x1 > page_rect.x1 - 1: new_rect.x1 = page_rect.x1 - 1
        if new_rect.width <= base.width:
            break
        y = page.insert_textbox(new_rect, text, fontsize=fontsize, align=align, render_mode=3, **font_kwargs)
        if y > 0:
            return True, new_rect
    return False, base

def pick_fontsize_height_then_fit(page: fitz.Page, rect: fitz.Rect, text: str, font_kwargs: dict,
                                  spans, min_size=6, max_size=120, align=0) -> tuple[int, fitz.Rect]:
    """
    1) Кегль ~ по высоте прямоугольника + соседним спанам
    2) Сначала расширяем прямоугольник под этот кегль
    3) Если не влезло — бинарно уменьшаем кегль в базовый rect
    Возвращает (fontsize, rect_for_draw)
    """
    # оценка кегля
    by_height = rect.height * 0.86
    by_spans  = dominant_fontsize(spans, rect)
    fs_guess  = int(max(min_size, min(max_size, max(by_height, by_spans))))

    # попытка расширять
    ok, rect_expanded = try_fit_by_expanding_rect(page, rect, text, fs_guess, font_kwargs, max_expand=100, step=2, align=align)
    if ok:
        return fs_guess, rect_expanded

    # фолбэк: уменьшаем кегль в базовую рамку
    pad = 0.5
    r_in = fitz.Rect(rect.x0 + pad, rect.y0 + pad, rect.x1 - pad, rect.y1 - pad)
    lo, hi, best = min_size, fs_guess, min_size
    while lo <= hi:
        mid = (lo + hi) // 2
        y = page.insert_textbox(r_in, text, fontsize=mid, align=align, render_mode=3, **font_kwargs)
        if y > 0:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return int(best), r_in

# ---------------------- Core replace loop ----------------------
def replace_text_everywhere(doc: fitz.Document, pairs, font_kwargs: dict, redact_fill=None, align=0) -> int:
    total_hits = 0
    for pnum, page in enumerate(doc, start=1):
        spans = collect_spans(page)
        hits = []

        # поиск
        for old, new in pairs:
            rects = search_phrase_rects(page, old)
            if not rects:
                print(f"❌ Стр.{pnum}: '{old}' не найден.")
                continue
            print(f"✅ Стр.{pnum}: {len(rects)} вхожд. для '{old}'.")
            hits.append((new, rects))

        if not hits:
            continue

        # замазка
        any_rects = False
        for _, rects in hits:
            for r in rects:
                annot = page.add_redact_annot(r, fill=redact_fill)
                annot.update()
                any_rects = True
        if any_rects:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # вставка
        for new_text, rects in hits:
            for r in rects:
                fs, r_draw = pick_fontsize_height_then_fit(page, r, new_text, font_kwargs, spans, align=align)
                page.insert_textbox(r_draw, new_text, fontsize=fs, align=align, **font_kwargs)
                print(f"   ↳ Стр.{pnum}: '{new_text}' fs={fs}, widthΔ≈{int(r_draw.width - r.width)}pt")
                total_hits += 1
    return total_hits

# ---------------------- UI ----------------------
def main():
    root = Tk(); root.withdraw()

    in_path = askopenfilename(title="Выберите исходный PDF", filetypes=[("PDF files", "*.pdf")])
    if not in_path:
        messagebox.showinfo("Отмена", "Файл не выбран."); return

    out_path = asksaveasfilename(
        title="Куда сохранить изменённый PDF",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=os.path.splitext(os.path.basename(in_path))[0] + "_updated.pdf",
    )
    if not out_path:
        messagebox.showinfo("Отмена", "Путь сохранения не выбран."); return

    try:
        font_path = pick_cyrillic_font_path()
    except Exception as e:
        messagebox.showerror("Шрифт", str(e)); return

    try:
        doc = fitz.open(in_path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть PDF:\n{e}"); return

    try:
        font_kwargs = get_font_kwargs(doc, font_path)  # {'fontname': 'F0'} или {'fontfile': '...'}
        print(f"[font] using: {font_kwargs}")

        # align=0 (left). При желании можно сменить на fitz.ALIGN_CENTER / fitz.ALIGN_RIGHT
        hits = replace_text_everywhere(doc, REPLACEMENTS, font_kwargs, redact_fill=None, align=0)

        # Сохранение (на старых версиях может не быть garbage=4)
        try:
            doc.save(out_path, deflate=True, garbage=4)
        except TypeError:
            doc.save(out_path, deflate=True)
        doc.close()

        msg = ("Совпадений не найдено.\n\nПроверьте точность строк и кавычки/пробелы."
               if hits == 0 else f"Готово! Заменено вхождений: {hits}\n\nСохранено в:\n{out_path}")
        messagebox.showinfo("Результат", msg)
    except Exception as e:
        try: doc.close()
        except: pass
        messagebox.showerror("Ошибка", f"Не удалось внести изменения:\n{e}")

if __name__ == "__main__":
    main()
