# Hackceler8 2024 Game

## Steps to run the game:

1. Install prerequisites
```
cd handout
python3 -m venv my_venv
source my_venv/bin/activate
pip3 install -r requirements.txt
```

2. Run server (optional but good for testing cheat detection/etc.)

```
cd handout
source my_venv/bin/activate
python3 server.py
```

Note that this server is slightly different from the one run by organizers during the live rounds as it doesn't have all the code for the boss fights.

3. Run client

```
cd handout
source my_venv/bin/activate
python3 client.py
```

If you want to run the client without a server, pass `--standalone` as an additional argument.

## kijitora カスタム
### デフォルトキーマップ

| キー | 動作 | 詳細・用途 |
| --- | --- | --- |
| Z | TickRate減らす | |
| X | TickRate増やす | |
| M | キーリプレイ停止 | |
| C | Tick停止 | |
| V | Tickを進める | |
| K | 無敵 | standaloneのみ |
| U | カメラリセット | |
| I | カメラズームイン | |
| O | カメラズームアウト | |
| Y | 自動ペイント | Piet疑惑 |
| H | Tick Undo | 10tickおき/arcadeで動きません |
| J | Tick Redo | |
| L | マップリセット | 用途は後述 |
| , | 複数Gunの連射 | |
| B | ボスにオートエイム | |
| N | 自動二段ジャンプ | |
| F | ジャンプ軌跡通りの最大ジャンプ | |
| T | キーロック | そのとき押してるキーを押し続ける。もう1度押すと解除 |
| 1-5 | ゲーム状態のセーブ/ロード | 5スロットそれぞれに保存可能,standaloneのみ |
| 6-0 | キー履歴のセーブ/ロード | 5スロットそれぞれに保存可能 |
| ctrl+数字 | スロットクリア | |

### その他機能
| 操作 | 動作 | 詳細・用途 |
| --- | --- | --- |
| 右クリック | テレポート | |
| 中クリック | 経路探索して移動 | Rust製でセットアップが必要 |
| ホイールスクロール | カメラズームイン/アウト | |
| Ctri+V | ペースト（テキスト入力画面） | コンソールから入力を受け付ける |

### HUD
- 左上：キー入力履歴
- 左下：上から順に 無敵とか自動ペイントフラグの表示、fps、水中とかのenv情報、プレイヤーの座標、現在のtick/サーバー側のtick/tickrate
- プレイヤーからの線：赤がアイテム、黄色がコイン
- 赤い円：敵の索敵範囲（遠距離攻撃の敵はプレイヤーがこの範囲内かつ向いている方向にプレイヤーがいる場合に撃つ、近距離攻撃の敵は範囲内にいる場合に距離に比例したダメージ）
- 壁についてるピンク：ダブルジャンプ可能の表示、Nキーを押しながらオブジェクトに向かって進むとこのオブジェクトの上端でダブルジャンプできる

### 覚えておくと良いこと
サーバーにパケットを180tick送らせて送信しているのでその分まではTick Undo/Redoができます
arcadeが存在する場合起動するために#sharedに貼っているコードのコピペが必要（開始時にpushします）
extra_itemsの適用は`config#extra_items`に追記が必要（開始時にpushします）

### path findingの実行方法
- rustup, maturin をインストール
- cheats-rust/build.shを実行
- 表示されるpip install ... を実行

### 実行時引数
  - `--stars [STARS]`: ゲーム起動時に所持しているスターの数を変更
  - `--go-boss`: ゲーム起動時にAキーを押しっぱなしにしてボス部屋に直行する（ボス部屋に入るtickを揃える用）

### How to use
基本的にローカルで動かすときは--standaloneモードで動かす想定（無敵、バックアップとかの機能はstandaloneじゃないと動かない）\
ダメージ受けたらTick Undo/Redoで戻ってやり直す、ゆっくり操作したいときはTickRate操作するかTick停止して1tickずつ進めていく感じ \
目的地点までたどり着けたらキー履歴を保存してよしなに共有する \
敵が弾を撃つ周期と向く方向はRキーのリセットでリセットされず、基本的にマップリセットをonにした状態でリセットしてから操作を始めないとキー履歴が正しくリプレイにならないので注意（デフォルトでonです）

自動ペイントはcalc_painting_target_image関数でターゲットとなる画像を計算しているので、使うときはこの関数を書き換える \
戻り値はintの二次元配列で、-1の場合空白、それ以外は PaintingSystem#all_colors の色を参照 \
Pencilを持った状態で自動ペイントをonにすると赤い枠が表示され自動で色を塗ってくれる（無重力を前提） \
すべての枠内のピクセルが白でハイライトされたらok

### 本番いじりそうな箇所
- ゲームが受け取るキー入力を改変したいときは `_pressed_key_hook`
- 適当なキー入力をhookしてなにか実行したいときは `macros#*_key_pressed` を書き換え
  - コードでマクロを生成して実行するみたいなのは`fire_all_guns`とかを参考に
  - 次tickの開始時になんかしたいみたいなのは`kstate.next_tick_tasks`に関数を追加
- なにか描画したいときは `render_hud`
