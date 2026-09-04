# English Drill Generator

## 概要
sample_data.xlsxのように| ID | Japanese | English |を入力し，main.pyを実行すると，Excelに登録した日本語・英語の例文から、英作文練習用の問題PDFと解答PDFを自動生成するPythonツールです．
過去の出題履歴を保存し，全問題が一度出題されるまで未出題の問題を優先して抽出します．従来の問題作成の効率を格段に上げ個人でのドリルの作成を可能にしました．

## 背景
問題集をExcelで管理している場合、

- 問題を毎回選ぶ
- Wordなどへコピーする
- レイアウトを整える
- PDFとして保存する

といった作業が必要になります。

本ツールではこれらをPythonで自動化しました。

## 主な機能

- Excelファイルの読み込み
- 問題のランダム抽出
- 過去の出題履歴の管理
- 未出題問題の優先抽出
- PDFの自動生成
- 日本語PDFへの対応

## 使用技術

- Python
- pandas
- openpyxl
- ReportLab

## 使用方法

1. `sample_data.xlsx` の形式で問題を入力します。

##入力例

| ID | Japanese | English |
|---|---|---|
| 1 | 私は学生です。 | I am a student. |
| 2 | 彼は東京に住んでいます。 | He lives in Tokyo. |

2. 必要なライブラリをインストールします。

pip install -r requirements.txt

3. プログラムを実行します。

python main.py

4. PDFが自動生成されます。

## 今後の改善

- GUIへの対応
- 問題数を画面上から変更可能にする
- PDFレイアウトのカスタマイズ

## ディレクトリ構成
english-drill-generator/
├── main.py
├── README.md
├── requirements.txt
├── .gitignore
├── sample_data.xlsx
│
├── samples/
│   ├── sample_question.pdf
│   └── sample_answer.pdf
│
└── output/
    ├── drill_20260904_....pdf
    └── answer_20260904_....pdf
