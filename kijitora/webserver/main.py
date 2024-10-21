import html
import subprocess
import time
from types import BuiltinFunctionType, BuiltinMethodType, FunctionType
from urllib.parse import quote, urlencode
from flask import Flask, jsonify, render_template, request
import os
import json

from game.components.npc.trapped_npc import TrappedNpc
from game.engine.generics import GenericObject
from game.map.tilemap import Coin, TileMap
from kijitora.keyhistory import KEY_HISTORY_DIR
from kijitora import config
from kijitora import kstate
from kijitora.config import DATA_DIR, KEY_REMAP_CONFIG_DIR, get_key_remap_name, set_key_remap, set_key_remap_by_name, set_key_remap_name
from kijitora.keyhistory import load_key_history_from_name
import logging
# import mod

conventional_name = {
  "jessse": "帽子ヘビ",
  "quackington": "デブヒヨコ",
  "raibbit": "巨大ウサギ",
  "trasher": "裸アライグマ",
  "casher": "紳士アライグマ",
  "trapped_jessse_npc": "帽子ヘビ",
  "trapped_quackington_npc": "デブヒヨコ",
  "trapped_raibbit_npc": "巨大ウサギ",
  "trapped_trasher_npc": "裸アライグマ",
  "trapped_casher_npc": "紳士アライグマ",
}

_client: "mod.HackedHx8Client" = None
app = Flask(__name__, template_folder=os.path.abspath(os.path.join(__file__, "..", "template")))
keyconfig = {}
print(os.path.abspath(os.path.join(__file__, "..", "template")))

@app.route('/settings/key-remap', methods=['POST'])
def set_keyconfig():
  if request.json is None:
    return jsonify({"status": "error", "message": "No JSON data provided"}), 400
  key_remap_name = request.json["key_remap_name"]
  if key_remap_name is None:
    return jsonify({"status": "error", "message": "No config name specified"}), 400

  set_key_remap_by_name(key_remap_name)
  return jsonify({"status": "success", "message": "Configuration loaded"}), 200

@app.route('/teleport', methods=['POST'])
def teleport():
  if request.json is None:
    return jsonify({"status": "error", "message": "No JSON data provided"}), 400
  map_name = request.json["map_name"]
  def teleporting_function(game):
    print("!", map_name)
    game.load_map(map_name)
  kstate.next_tick_tasks.append(teleporting_function)
  return jsonify({"status": "success", "message": "Teleported"}), 200

@app.route('/start-replay', methods=['POST'])
def start_replay():
  if request.form is None:
    return jsonify({"status": "error", "message": "No JSON data provided"}), 400
  kstate.loading_key_history_from = request.form["replay_file"]
  _, label = load_key_history_from_name(kstate.loading_key_history_from)
  kstate.reset_delay = label == _client.game.current_map
  return jsonify({"status": "success", "message": "Configuration loaded"}), 200

@app.route('/open-replay', methods=['POST'])
def open_replay():
  subprocess.run(["open", KEY_HISTORY_DIR])
  return ""

@app.route("/gameinfo")
def get_gameinfo():
  collected_npcs = [flag for flag in _client.game.match_flags.flags if flag.collected_time > 0 and not flag.name.endswith("_boss")]
  item_names = set(item.name for item in _client.game.items)

  npc_names = ["trapped_" + flag.name + "_npc" for flag in collected_npcs]

  html = ""
  for map_name, map_attr in _client.game.original_maps_dict.items():
    html += f'<li><a href="#" onclick="postTeleport(\'{map_name}\')">{map_name}</a><ul>'
    for npc in map_attr.tiled_map.objects:
      if not isinstance(npc, TrappedNpc): continue
      html += f'<li {"style=\"color:gray;font-weight:900\"" if npc.name in npc_names else "style=\"font-weight:900\""}>{conventional_name.get(npc.name, npc.name)}({npc.x},{npc.y},stars={npc.stars})</li>' 
    for coin in TileMap.coins:
      if coin.lvl != map_name: continue
      obtained = "coin_" + coin.id in item_names
      html += f'<li {"style=\"color:gray;\"" if obtained else ""}>Coin({coin.x},{coin.y})</li>'
    html += "</ul></li>"

  return f"""
  #{_client.game.tics} / {time.time()}
  <h2>Notable Objects (obtained if gray)</h2>
  <ul><li>stars / boss required: {sum([npc.stars for npc in collected_npcs])}/{_client.game.match_flags.stars_for_boss}({",".join([conventional_name.get(npc.name, npc.name) for npc in collected_npcs])})</li></ul>
  <ul>{html}</ul>
  <h2>Savestate</h2>
  <ul>{''.join([f'<li>{slot}: {kstate.game_backups.get(slot, (None, None))[1]}</li>' for slot in config.savestate_slots])}</ul>
  <h2>Replay</h2>
  <ul>{''.join([f'<li>{slot}: {kstate.key_history_slots.get(slot)}</li>' for slot in config.replay_slots])}</ul>
  """

class __Neko:
  def nekoneko():
    pass
MethodType = type(__Neko().nekoneko)

def is_useful_variables(prop: str, val):
    if prop.startswith('__') and prop.endswith('__'): return False
    if isinstance(val, FunctionType): return False
    if isinstance(val, BuiltinFunctionType): return False
    if isinstance(val, MethodType): return False
    return True

def my_repr(obj):
  if isinstance(obj, GenericObject):
    return f"{obj.nametype}({obj.name}, {obj.x}, {obj.y})"
  return repr(obj)

@app.route("/objinfo")
def objinfo():
  reload = "" if request.args.get('reload') is None else "&reload=" + request.args.get('reload', "")
  obj = _client

  path = request.args.get('path')
  if not path:
    path = "obj"
  try:
    s = path.splitlines(True)
    exec("".join(s[:-1]))
    obj = eval(s[-1])
  except Exception as e:
    return repr(e)

  additional_info = ""
  if isinstance(obj, list) or isinstance(obj, tuple):
    additional_info += "<h2>list items</h2>\n"
    additional_info += "<ul>\n"
    for (idx, value) in enumerate(obj):
      additional_info += f'<li>{idx}: <a href="/objview?path={quote(path)}[{idx}]{reload}">{html.escape(my_repr(value))}</a></li>\n'
    additional_info += "</ul>\n"
  elif isinstance(obj, dict):
    additional_info += "<h2>dict items</h2>\n"
    additional_info += "<dl>\n"
    for (idx, (key, value)) in enumerate(obj.items()):
      additional_info += f"<dt>{html.escape(repr(key))}</dt>\n"
      additional_info += f'<dd><a href="/objview?path={quote(path)}[{quote(repr(key))}]{reload}">{html.escape(my_repr(value))}</a></dd>\n'
    additional_info += "</dl>\n"

  child_properties = dir(obj)
  links = [f'<li><a href="/objview?path={quote(path) + "." if path else ""}{quote(prop)}{reload}">{html.escape(prop)}</a>: {html.escape(my_repr(getattr(obj, prop)))}</li>' for prop in child_properties if is_useful_variables(prop, getattr(obj, prop))]
  return f"""
  <h2>Object Viewer: {html.escape(my_repr(obj))}</h2>
  <ul>{''.join(links)}</ul>
  {additional_info}
  """

@app.route("/objview")
def objview():
  return render_template("objview.html")

@app.route("/")
def index():
  remap_files = os.listdir(KEY_REMAP_CONFIG_DIR)
  replay_files = [f for f in os.listdir(KEY_HISTORY_DIR) if f.endswith('.txt') and not f.startswith("keyhistory")]
  return render_template(
    "index.html",
    **{
      "remap_default_value": get_key_remap_name(),
      "remap_files": remap_files,
      "replay_files": replay_files,
    }
  )

def run_server(client):
  global _client
  _client = client
  log = logging.getLogger('werkzeug')
  log.setLevel(logging.ERROR)
  app.run(port=13337, debug=True, use_reloader=False)
