# Windows 11 の自動スリープ時間を Python から変更する

Windows 標準の `powercfg` を Python の標準ライブラリから呼び出す短いサンプルです。追加の Python ライブラリは不要です。現在有効な電源プランの「無操作でスリープするまでの時間」を変更します。

## 実行方法

このディレクトリで PowerShell を開きます。仮想環境 `.venv` がまだなければ作成し、その Python で実行します。仮想環境の有効化操作は不要です。

```powershell
uv venv .venv
.\.venv\Scripts\python.exe .\main.py --ac 0 --dc 0
.\.venv\Scripts\python.exe .\main.py --ac 30 --dc 15
.\.venv\Scripts\python.exe .\main.py --ac 30
.\.venv\Scripts\python.exe .\main.py --dc 15
.\.venv\Scripts\python.exe .\main.py --show
.\.venv\Scripts\python.exe .\main.py --restore
```

- `--ac` は電源接続時、`--dc` はバッテリー時。単位は分です。どちらか一方だけを指定した場合、もう一方は変更しません。
- `0` は自動スリープなしです。負数・整数以外は受け付けません。
- 最初の変更前に、対象電源プランと AC/DC の元の値を `%LOCALAPPDATA%\windows-sleep-timeout-python\snapshot.json` に保存します。その後の変更でも、復元するまでは最初の値を保持します。
- `--show` は現在の電源プランと AC/DC の値を秒単位で表示します。`--restore` は保存した両方の値を正確に復元し、成功後に保存データを削除します。Python を終了した後でも復元できます。
- エラーがなければ終了コードは0です。両方を指定した場合は AC、DC の順に変更します。途中で失敗した場合、保存データは残ります。`--restore` で再試行できます。
- 復元前に別の電源プランへ切り替えた場合、保存した元のプランの値を復元します。現在選択中のプランは切り替えません。保存データがある間、別のプランへの新規変更はできません。
- 画面消灯、休止状態、ふたを閉じたときの動作は変更しません。

## Python の処理に組み込む

`sleep_settings.py` が import 用のライブラリで、`main.py` が CLI です。次の例の `long_task.py` などは、実際に実行する処理のファイル名に置き換えてください。

### 現在の設定を読み取る

```python
from sleep_settings import SleepTimeoutManager

manager = SleepTimeoutManager()
current = manager.read()
print(current.scheme_guid)
print(current.ac_seconds, current.dc_seconds)  # 単位は秒
```

### 別の処理が動いている間だけ変更する

```python
import subprocess
import sys
from sleep_settings import SleepTimeoutManager

manager = SleepTimeoutManager()
with manager.temporary(ac_minutes=0, dc_minutes=0):
    subprocess.run([sys.executable, "long_task.py"], check=True)
```

処理が正常終了しても例外で終了しても、`with` を抜けると元の設定に戻ります。`temporary()` は未復元の保存データがある状態では開始できません。

### 複数の処理で設定を変え、最後に戻す

```python
import subprocess
import sys
from sleep_settings import SleepTimeoutManager

manager = SleepTimeoutManager()
if manager.saved_snapshot() is not None:
    raise RuntimeError("先に未復元の設定を戻してください")
try:
    manager.set(ac_minutes=60)
    subprocess.run([sys.executable, "first_task.py"], check=True)
    manager.set(dc_minutes=30)
    subprocess.run([sys.executable, "second_task.py"], check=True)
finally:
    if manager.saved_snapshot() is not None:
        manager.restore()
```

最初の `set()` 時点の AC/DC 両方の値が保存され、次の `set()` では上書きされません。どちらかの処理が失敗しても `finally` で復元します。

### 別の Python 実行から戻す

```python
# 変更する側。元設定はファイルに保存される
from sleep_settings import set_sleep_timeout

set_sleep_timeout(ac_minutes=0)
```

```python
# 後で起動する別のスクリプト
from sleep_settings import SleepTimeoutManager

SleepTimeoutManager().restore()
```

保存先は同じユーザーの `%LOCALAPPDATA%\windows-sleep-timeout-python\snapshot.json` です。保存ファイルが壊れている場合は変更・復元を止め、ファイルを調べてから対応してください。同じ保存先を使う複数プロセスからの同時変更は対象外です。

## 仮想環境

`venv` や `uv venv` 内でも使えます。このスクリプトは Python 標準ライブラリと、仮想環境の外にある Windows の `powercfg` を使います。仮想環境にライブラリを追加する必要はありません。既に別の仮想環境がある場合は、その `Scripts\python.exe` に読み替えてください。仮想環境を有効化済みなら `python .\main.py --ac 0 --dc 30` でも実行できます。

## 仮想環境を使わない場合

ホストの Python が `python` コマンドで使える場合は、仮想環境を作らずに実行できます。

```powershell
python .\main.py --ac 0 --dc 30
```

この PC のように `python` が Microsoft Store のエイリアスの場合は、`uv` で仮想環境以外の Python を明示的に探して実行します。`--system` を付けない `uv python find` は、カレントディレクトリの `.venv` を選ぶことがあります。

```powershell
$hostPython = uv python find --system 3.14
& $hostPython .\main.py --ac 0 --dc 30
```

設定を読むときは `--show` または `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` を実行します。設定アプリでの目視確認は [MANUAL_TEST.md](MANUAL_TEST.md) を参照してください。

参照：[Microsoft の powercfg コマンド仕様](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options)。
