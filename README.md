# KovaaksTracker

KovaaK'sのシナリオごとのプレイ回数を集計し、100回ごとにレベルアップするゲーム風の回数管理ソフトです。
ローカルのCSVファイルを集計して表示する機能を中心に、将来的には kovaaks.com からリーダーボード情報を取得する拡張性も持たせています。

## MVP版の機能
- ローカルの `stats` フォルダ内のCSVを解析・集計
- 累計プレイ回数に応じたレベル表示（100回 = 1レベル）と全シナリオの「総合Level表示」
- ベストスコアと最終プレイ日時、次レベルまでの回数の表示
- kovaaks.comのAPIからの正確なWebデータ(Entries, Rank, Top %, Tier)取得機能
- SQLiteによるデータの永続化と、`stats` フォルダの自動探索
- シナリオ名でのリアルタイム曖昧検索と、Tier/Rank/プレイ回数等に沿った高度なソート機能

## 想定フォルダ構成
```text
(任意の親フォルダ)
 ├── stats/ （自動探索対象）
 └── KovaaksTracker/
      ├── main.py
      ├── ui.py
      ├── parser.py
      ├── config.py
      ├── database.py
      ├── web_fetcher.py
      ├── requirements.txt
      └── README.md
```

## セットアップ手順
1. Python 3.9以上がインストールされていることを確認します。
2. コマンドプロンプト等で本フォルダを開き、以下のコマンドを実行して依存ライブラリをインストールします。
```cmd
pip install -r requirements.txt
```

## 実行手順
```cmd
python main.py
```
起動すると自動で `stats` フォルダを探索します。
見つからない場合は、画面右上の「Select Stats Folder」から手動で指定できます。
「Refresh Local Data」を押すことで、CSVデータを読み込みなおしてリストを更新します。

4. 「Sort By」ドロップダウンからTier(高い順・低い順)などでリストを並び替えることができます。

## アプリのロゴ(アイコン)設定
アプリの実行フォルダ（`main.py` と同じ階層）、または `assets/` フォルダ内に **`KovaaksTrackerLogo.ico`** という名前で画像ファイルを配置すると、自動的にUIウィンドウの左上アイコンとして読み込まれます。

## exe化手順（将来用）
PyInstallerを使用して、ユーザーがPython不要で動かせる単一のexeファイルにすることができます。
もしカスタムアイコンを適用してexe化する場合は以下のようにビルドします。
```cmd
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=assets\KovaaksTrackerLogo.ico main.py
```
ビルド完了後、`dist/main.exe` が生成されます。
