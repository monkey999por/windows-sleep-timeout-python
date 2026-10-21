# Windows 11 の自動スリープ時間を Python から変更する

Windows 標準の `powercfg` を Python の標準ライブラリから呼び出す短いサンプルです。追加の Python ライブラリは不要です。現在有効な電源プランの「無操作でスリープするまでの時間」を変更します。

## 実行方法

このディレクトリで PowerShell を開きます。仮想環境 `.venv` がまだなければ作成し、その Python で実行します。仮想環境の有効化操作は不要です。

```powershell
uv venv .venv
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 0 --dc 0
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 30 --dc 15
.\.venv\Scripts\python.exe .\sleep_settings.py --ac 30
.\.venv\Scripts\python.exe .\sleep_settings.py --dc 15
```

- `--ac` は電源接続時、`--dc` はバッテリー時。単位は分です。どちらか一方だけを指定した場合、もう一方は変更しません。
- `0` は自動スリープなしです。負数・整数以外は受け付けません。
- エラーがなければ終了コードは0です。両方を指定した場合は AC、DC の順に変更します。途中で失敗すると先に成功した変更は残るため、必要に応じて元の値を再設定してください。
- 画面消灯、休止状態、ふたを閉じたときの動作は変更しません。

Python コードからも呼び出せます。

```python
from sleep_settings import set_sleep_timeout

set_sleep_timeout(ac_minutes=0, dc_minutes=30)
```

## 仮想環境

`venv` や `uv venv` 内でも使えます。このスクリプトは Python 標準ライブラリと、仮想環境の外にある Windows の `powercfg` を使います。仮想環境にライブラリを追加する必要はありません。既に別の仮想環境がある場合は、その `Scripts\python.exe` に読み替えてください。仮想環境を有効化済みなら `python .\sleep_settings.py --ac 0 --dc 30` でも実行できます。

設定を読むときは `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` を実行します。設定アプリでの目視確認と元の値への戻し方は [MANUAL_TEST.md](MANUAL_TEST.md) を参照してください。

参照：[Microsoft の powercfg コマンド仕様](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options)。
