# Windows の設定画面で確認する手順

この手順は、スクリプトによる変更を Windows の設定アプリとコントロールパネルで目視確認するためのものです。各変更後、確認画面を一度閉じて開き直してください。

## 変更前

PowerShell でこのファイルがあるディレクトリに移動します。`.venv` がまだない場合だけ `uv venv .venv` で作成します。以下のスクリプト実行はすべて `.venv` 内の Python を指定します。既存の別の仮想環境を使う場合は、`Scripts\python.exe` のパスを読み替えてください。

まず仮想環境の Python と、変更前の AC/DC のスリープ時間を確認します。

```powershell
.\.venv\Scripts\python.exe --version
powercfg /getactivescheme
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

`Current AC Power Setting Index` と `Current DC Power Setting Index`（日本語環境では対応する AC/DC の設定値）が、16進数表記の**秒数**です。例えば `0x00000000` は「なし」、`0x00000a8c` は2700秒＝45分です。開始時の値を記録し、最後に同じ値へ戻します。この PC の前回確認値は AC 0分、DC 45分ですが、実際の作業開始時の値を優先してください。

## 変更して画面で確認

以下を1行ずつ実行します。各コマンドの終了コードは PowerShell の `$LASTEXITCODE` で確認できます。`0` 以外の場合は次へ進まず、エラーを確認してください。

```powershell
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 30 --dc 30
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 0 --dc 0
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 30
.\.venv\Scripts\python.exe .\sleep_settings.py --dc 15
```

| 実行後 | 電源接続時（AC） | バッテリー時（DC） |
|---|---|---|
| 両方30分 | 30分 | 30分 |
| 両方なし | なし | なし |
| ACのみ変更 | 30分 | なし |
| DCのみ変更 | 30分 | 15分 |

### Windows 設定アプリ

`Win + I` →「システム」→「電源とバッテリー」→「画面、スリープ、休止状態のタイムアウト」で、電源接続時・バッテリー時の**スリープ**項目を確認します。Windows のバージョンにより表示名が異なることがあります。

### コントロールパネル

`Win + R` → `powercfg.cpl` → Enter → 使用中のプランの「プラン設定の変更」→「コンピューターをスリープ状態にする」を確認します。バッテリーがない PC では DC 欄が表示されないことがあります。

## 元に戻す

最初に記録した AC/DC が整数の分数なら、その値を指定して元に戻します。例えば開始時に AC 0分、DC 45分だった場合は次を実行します。

```powershell
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 0 --dc 45
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

開始時の値が分単位で割り切れない場合は、記録した**秒数を10進数に変換**し、以下の `<AC秒数>` と `<DC秒数>` に入れて復元します。

```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE <AC秒数>
powercfg /setdcvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE <DC秒数>
powercfg /setactive SCHEME_CURRENT
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

復元後は、最初に記録した値とコマンド出力および両確認画面が一致することを確認してください。スリープ移行までの待機試験はこの手順に含みません。
