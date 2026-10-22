# Windows の設定画面で確認する手順

この手順は、スクリプトによる変更を Windows の設定アプリとコントロールパネルで目視確認するためのものです。各変更後、確認画面を一度閉じて開き直してください。

## 変更前

PowerShell でこのファイルがあるディレクトリに移動します。次のどちらか一方を選び、以降のコマンドで使う Python を `$sleepPython` に設定します。

**仮想環境を使う場合**：`.venv` がまだなければ `uv venv .venv` で作成し、以下を実行します。既存の別の仮想環境ならその `Scripts\python.exe` のパスに読み替えます。

```powershell
$sleepPython = '.\.venv\Scripts\python.exe'
```

**仮想環境を使わない場合**：ホストの Python が `python` コマンドで使えるなら `$sleepPython = 'python'` とします。この PC のように `python` が Microsoft Store のエイリアスの場合は、次のように `uv` からホストの Python を指定します。

```powershell
$sleepPython = uv python find --system 3.14
```

まず選んだ Python と、変更前の AC/DC のスリープ時間を確認します。`sys.prefix == sys.base_prefix` はホスト実行なら `True`、仮想環境なら `False` です。

```powershell
& $sleepPython --version
& $sleepPython -c 'import sys; print(sys.prefix == sys.base_prefix)'
& $sleepPython .\main.py --show
powercfg /getactivescheme
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

`Current AC Power Setting Index` と `Current DC Power Setting Index`（日本語環境では対応する AC/DC の設定値）が、16進数表記の**秒数**です。例えば `0x00000000` は「なし」、`0x00000a8c` は2700秒＝45分です。`--show` の結果も記録します。以前の変更で未復元の保存データがある場合は、開始前に `--restore` を実行してください。

## 変更して画面で確認

以下を1行ずつ実行します。各コマンドの終了コードは PowerShell の `$LASTEXITCODE` で確認できます。`0` 以外の場合は次へ進まず、エラーを確認してください。

```powershell
& $sleepPython .\main.py --ac 30 --dc 30
& $sleepPython .\main.py --ac 0 --dc 0
& $sleepPython .\main.py --ac 30
& $sleepPython .\main.py --dc 15
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

最初の変更前に記録された値を、`--restore` で秒単位のまま元に戻します。成功後、復元用の保存データは削除されます。

```powershell
& $sleepPython .\main.py --restore
& $sleepPython .\main.py --show
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

`--restore` に失敗した場合は復元データが残るため、原因を確認して再実行します。保存データを利用できない場合に限り、開始時に記録した**秒数を10進数に変換**し、以下の `<AC秒数>` と `<DC秒数>` に入れて手動で復元します。

```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE <AC秒数>
powercfg /setdcvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE <DC秒数>
powercfg /setactive SCHEME_CURRENT
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
```

復元後は、最初に記録した値とコマンド出力および両確認画面が一致することを確認してください。スリープ移行までの待機試験はこの手順に含みません。
