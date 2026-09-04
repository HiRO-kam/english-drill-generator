from pathlib import Path
from datetime import datetime

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


# =========================
# 設定

BASE_DIR = Path(__file__).parent
EXCEL_FILE = BASE_DIR / "sample_data.xlsx"
HISTORY_FILE = BASE_DIR / "history.xlsx"

ID_COLUMN = "ID"
JAPANESE_COLUMN = "Japanese"
ENGLISH_COLUMN = "English"

NUMBER_OF_QUESTIONS = 15

# 毎回違う問題にする場合は None
# 同じ問題を再現したい場合は 1234 などの整数を指定
RANDOM_SEED = None

# 問題文のフォントサイズ
QUESTION_FONT_SIZE = 10.5

# 解答のフォントサイズ
ANSWER_FONT_SIZE = 9.5

#紙面設定
PDF_FONT_NAME = "HeiseiKakuGo-W5"

LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
TOP_MARGIN = 13 * mm
BOTTOM_MARGIN = 12 * mm

NUMBER_WIDTH = 9 * mm

# =========================
# Excelの読み込み
# =========================

def load_examples(excel_file: Path) -> pd.DataFrame:
    """Excelから日本語文と英文を読み込む。"""

    if not excel_file.exists():
        raise FileNotFoundError(
            f"{excel_file} が見つかりません。\n"
            "main.pyと同じフォルダに置いてください。"
        )

    df = pd.read_excel(excel_file)

    required_columns = {
    ID_COLUMN,
    JAPANESE_COLUMN,
    ENGLISH_COLUMN,
}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Excelに必要な列がありません。\n"
            f"不足している列: {', '.join(missing_columns)}"
        )

    # 空欄の行を削除
    df = df.dropna(subset=[JAPANESE_COLUMN, ENGLISH_COLUMN])

    # 前後の余分な空白を削除
    df[JAPANESE_COLUMN] = df[JAPANESE_COLUMN].astype(str).str.strip()
    df[ENGLISH_COLUMN] = df[ENGLISH_COLUMN].astype(str).str.strip()

    # 完全な空文字列を削除
    df = df[
        (df[JAPANESE_COLUMN] != "")
        & (df[ENGLISH_COLUMN] != "")
    ]

    if len(df) < NUMBER_OF_QUESTIONS:
        raise ValueError(
            f"有効な例文が{len(df)}個しかありません。\n"
            f"{NUMBER_OF_QUESTIONS}問以上入力してください。"
        )

    df[ID_COLUMN] = pd.to_numeric(
    df[ID_COLUMN],
    errors="raise",
).astype(int)

    return df.reset_index(drop=True)


# =========================
# ランダム抽出
# =========================

def select_questions(
    df: pd.DataFrame,
    appeared_ids: set[int],
) -> tuple[pd.DataFrame, set[int]]:

    all_ids = set(df[ID_COLUMN])

    # 未出題ID
    unanswered_ids = all_ids - appeared_ids

    # -----------------------
    # 未出題が15問以上
    # -----------------------
    if len(unanswered_ids) >= NUMBER_OF_QUESTIONS:

        selected = (
            df[df[ID_COLUMN].isin(unanswered_ids)]
            .sample(
                n=NUMBER_OF_QUESTIONS,
                random_state=RANDOM_SEED,
            )
        )

        appeared_ids |= set(selected[ID_COLUMN])

    # -----------------------
    # 未出題が15問未満
    # -----------------------
    else:

        # 未出題は全部採用
        unanswered = df[
            df[ID_COLUMN].isin(unanswered_ids)
        ]

        # 補充数
        supplement_num = (
            NUMBER_OF_QUESTIONS
            - len(unanswered)
        )

        # 一巡終了なので履歴リセット
        appeared_ids = set()

        # 補充問題
        supplement = (
            df[
                ~df[ID_COLUMN].isin(
                    unanswered[ID_COLUMN]
                )
            ]
            .sample(
                n=supplement_num,
                random_state=RANDOM_SEED,
            )
        )

        selected = pd.concat(
            [
                unanswered,
                supplement,
            ]
        )

        # 次の一巡では補充分だけ出題済み
        appeared_ids |= set(supplement[ID_COLUMN])

        # PDF内もシャッフル
        selected = selected.sample(
            frac=1,
            random_state=RANDOM_SEED,
        )

    return (
        selected.reset_index(drop=True),
        appeared_ids,
    )

def load_history(history_file: Path) -> set[int]:
    """過去に出題された問題IDを読み込む。"""

    if not history_file.exists():
        return set()

    history_df = pd.read_excel(history_file)

    if ID_COLUMN not in history_df.columns:
        return set()

    return set(history_df[ID_COLUMN].dropna().astype(int))

def save_history(
    appeared_ids: set[int],
    history_file: Path,
) -> None:
    """出題済みIDをExcelに保存する。"""

    history_df = pd.DataFrame(
        {
            ID_COLUMN: sorted(appeared_ids)
        }
    )

    history_df.to_excel(
        history_file,
        index=False,
    )
# =========================
# 文字列の折り返し
# =========================

def wrap_text(
    text: str,
    font_name: str,
    font_size: float,
    max_width: float,
) -> list[str]:
    """
    PDF上の横幅を測りながら文字列を折り返す。
    日本語でも英語でも使用できる。
    """

    lines: list[str] = []
    current_line = ""

    for character in text:
        candidate = current_line + character
        width = pdfmetrics.stringWidth(
            candidate,
            font_name,
            font_size,
        )

        if width <= max_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
            current_line = character

    if current_line:
        lines.append(current_line)

    return lines


# =========================
# 問題PDF
# =========================

def create_question_pdf(
    questions: pd.DataFrame,
    output_file: Path,
) -> None:
    """日本語のみを掲載したA4片面の問題PDFを作る。"""

    page_width, page_height = A4

    pdf = canvas.Canvas(
        str(output_file),
        pagesize=A4,
    )

    pdf.setTitle("English Drill")

    content_width = page_width - LEFT_MARGIN - RIGHT_MARGIN

    # タイトル
    pdf.setFont(PDF_FONT_NAME, 15)
    pdf.drawString(
        LEFT_MARGIN,
        page_height - TOP_MARGIN,
        "英作文ドリル",
    )

    pdf.setFont(PDF_FONT_NAME, 9)
    pdf.drawRightString(
        page_width - RIGHT_MARGIN,
        page_height - TOP_MARGIN,
        f"{NUMBER_OF_QUESTIONS}問",
    )

    # 氏名欄
    name_y = page_height - TOP_MARGIN - 8 * mm

    pdf.setFont(PDF_FONT_NAME, 9)
    pdf.drawString(LEFT_MARGIN, name_y, "氏名：")

    pdf.line(
        LEFT_MARGIN + 13 * mm,
        name_y - 1 * mm,
        page_width - RIGHT_MARGIN,
        name_y - 1 * mm,
    )

    # 問題を配置できる領域
    questions_top = name_y - 7 * mm
    usable_height = questions_top - BOTTOM_MARGIN

    # 15問を均等配置
    block_height = usable_height / len(questions)

    for index, row in questions.iterrows():
        number = index + 1
        japanese = row[JAPANESE_COLUMN]

        block_top = questions_top - index * block_height

        number_width = NUMBER_WIDTH
        text_x = LEFT_MARGIN + number_width
        text_width = content_width - number_width

        pdf.setFont(PDF_FONT_NAME, QUESTION_FONT_SIZE)
        pdf.drawString(
            LEFT_MARGIN,
            block_top,
            f"{number}.",
        )

        lines = wrap_text(
            japanese,
            PDF_FONT_NAME,
            QUESTION_FONT_SIZE,
            text_width,
        )

        line_height = 5.3 * mm

        for line_index, line in enumerate(lines[:2]):
            pdf.drawString(
                text_x,
                block_top - line_index * line_height,
                line,
            )

        # 英文を書き込む線
        answer_line_y = block_top - block_height + 5.0 * mm

        pdf.setLineWidth(0.5)
        pdf.line(
            text_x,
            answer_line_y,
            page_width - RIGHT_MARGIN,
            answer_line_y,
        )

    pdf.save()


# =========================
# 解答PDF
# =========================

def create_answer_pdf(
    questions: pd.DataFrame,
    output_file: Path,
) -> None:
    """問題と英文を掲載した解答PDFを作る。"""

    page_width, page_height = A4

    pdf = canvas.Canvas(
        str(output_file),
        pagesize=A4,
    )

    pdf.setTitle("English Drill Answers")

    content_width = page_width - LEFT_MARGIN - RIGHT_MARGIN

    pdf.setFont(PDF_FONT_NAME, 15)
    pdf.drawString(
        LEFT_MARGIN,
        page_height - TOP_MARGIN,
        "英作文ドリル 解答",
    )

    answers_top = page_height - TOP_MARGIN - 10 * mm
    usable_height = answers_top - BOTTOM_MARGIN
    block_height = usable_height / len(questions)

    for index, row in questions.iterrows():
        number = index + 1
        japanese = row[JAPANESE_COLUMN]
        english = row[ENGLISH_COLUMN]

        block_top = answers_top - index * block_height

        number_width = 9 * mm
        text_x = LEFT_MARGIN + number_width
        text_width = content_width - number_width

        pdf.setFont(PDF_FONT_NAME, 8.5)
        pdf.drawString(
            LEFT_MARGIN,
            block_top,
            f"{number}.",
        )

        japanese_lines = wrap_text(
            japanese,
            PDF_FONT_NAME,
            8.5,
            text_width,
        )

        pdf.drawString(
            text_x,
            block_top,
            japanese_lines[0],
        )

        pdf.setFont(PDF_FONT_NAME, ANSWER_FONT_SIZE)

        english_lines = wrap_text(
            english,
            PDF_FONT_NAME,
            ANSWER_FONT_SIZE,
            text_width,
        )

        # 英文は日本語の下に表示
        answer_y = block_top - 4.2 * mm

        for line_index, line in enumerate(english_lines[:2]):
            pdf.drawString(
                text_x,
                answer_y - line_index * 3.8 * mm,
                line,
            )

    pdf.save()

# =========================
# メイン処理
# =========================

def main() -> None:
    pdfmetrics.registerFont(
        UnicodeCIDFont("HeiseiKakuGo-W5")
    )

    df = load_examples(EXCEL_FILE)

    # 過去の履歴を読み込む
    appeared_ids = load_history(HISTORY_FILE)

    questions, appeared_ids = select_questions(
        df,
        appeared_ids,
    )

    save_history(
        appeared_ids,
        HISTORY_FILE,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    question_pdf = BASE_DIR / f"drill_{timestamp}.pdf"
    answer_pdf = BASE_DIR / f"answer_{timestamp}.pdf"

    create_question_pdf(
        questions,
        question_pdf,
    )

    create_answer_pdf(
        questions,
        answer_pdf,
    )

    all_ids = set(
        df[ID_COLUMN].astype(int).tolist()
    )

    missing_ids = all_ids - appeared_ids

    current_ids = set(
    questions[ID_COLUMN]
)

    print("今回の出題ID：")
    print(sorted(current_ids))

    print()
    print("作成が完了しました。")
    print(f"問題PDF: {question_pdf.resolve()}")
    print(f"解答PDF: {answer_pdf.resolve()}")
    print(f"出題済み：{len(appeared_ids)}問")
    print(f"未出題：{len(missing_ids)}問")

    if not missing_ids:
        print("全問題が一度以上出題されました！")
    else:
        print("未出題ID：")
        print(sorted(missing_ids))

if __name__ == "__main__":
    main()
