#!/usr/bin/python3

import asyncio
import atexit
import json
import os
import time
import traceback

import simpleobsws
from simpleobsws import Request
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
import tkinter as tk
from tkinter import simpledialog

ASSETS_PATH = os.path.join(os.path.dirname(__file__), "Assets")
run = True
scenes = {}
currentScene = ""
currentPreviewScene = ""
studioMode = False
muted_sources = {"", "", ""}
source_render_data = {"": {"current": False, "scene": "", "state": False, "scenes": {"": False}}}

loop = asyncio.get_event_loop()
while len(DeviceManager().enumerate()) < 1:
    time.sleep(0.5)
deck = DeviceManager().enumerate().pop()
deck.open()
deck.set_brightness(100)


async def update_all_keys():
    for j in range(0, deck.key_count()):
        await update_key_image(j, False)


def exit_handler():
    deck.close()
    print("Try Disconnect")
    loop.run_until_complete(ws.disconnect())
    print("Disconnected")
    loop.stop()
    loop.close()


async def exit_async():
    deck.reset()
    deck.close()
    await ws.disconnect()
    loop.stop()
    loop.close()
    os.exit()


# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
async def render_key_image(icon_filetype: str, font_filetype: str, label_text: str, deactivated: bool,
                           color: str = None):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    icon = Image.open(icon_filetype)
    if deactivated:
        icon.putalpha(70)
    image = PILHelper.create_scaled_image(deck, icon, margins=[0, 0, 20, 0])

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image a few pixels from the bottom of the key.
    draw = ImageDraw.Draw(image)
    if color is not None:
        draw.ellipse((0, 0, 10, 10), fill=color)

    font = ImageFont.truetype(font_filetype, 15)
    lines = len(label_text.splitlines())
    draw.text((image.width / 2, image.height - 5 - (lines - 1) * 15), text=label_text, font=font, anchor="ms",
              fill="white", stroke_width=0, spacing=1, align="center")

    return PILHelper.to_native_format(deck, image)


# Creates a new key image based on the key index, style and current key state
# and updates the image on the StreamDeck.
async def update_key_image(key, state):
    # Determine what icon and label to use on the generated key.
    key_style = await get_key_style(key, state)

    # Generate the custom key with the requested image and label.
    image = await render_key_image(key_style["icon"], key_style["font"], key_style["label"], key_style["deactivated"],
                                   key_style["highlight"])

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)


async def get_key_style(key, state):
    font: str = "NotoSans-Regular.ttf"
    icon: str = "default.png"
    label: str = ""
    # noinspection PyTypeChecker
    highlight: str = None
    state: bool
    deactivated: bool = False

    # print("Key update: "+ str(studioMode))

    key_data = data.get(str(key), {})
    label = key_data.get("Label", label)
    icon = key_data.get("Icon", icon)
    local_key_type: str = key_data.get("type", "None")
    if local_key_type == "Scene":
        if studioMode:
            if key_data["Name"] == currentPreviewScene:
                state = True
            elif key_data["Name"] == currentScene:
                highlight = "red"
        else:
            if key_data["Name"] == currentScene:
                state = True
    elif local_key_type == "StudioMode" and studioMode:
        state = True
    elif local_key_type == "MuteSource":
        if key_data["Name"] in muted_sources:
            state = True
    elif (local_key_type == "Render") or (local_key_type == "SongShow"):
        source_data = source_render_data[key_data["Name"]]
        if source_data["current"]:
            if currentScene in source_data["scenes"]:
                state = source_data["scenes"][currentScene]
            else:
                deactivated = True
        else:
            state = source_data["state"]
    elif local_key_type == "SongNumber":
        state = True

    if local_key_type == "SongShow":
        response = await requestAsync("GetInputSettings",{"inputName":"LiedText"})
        label = response["inputSettings"]["text"][11:]

    # print(str(key) + str(state))
    if state:
        icon = key_data.get("Icon-aktiv", icon)

    # print(icon)
    return {
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": font,
        "label": label,
        "highlight": highlight,
        "deactivated": deactivated
    }


async def switch_scene(key):
    global data
    global ws
    global studioMode
    global currentPreviewScene
    local_scene_name = data[key]["Name"]
    payload = {"sceneName": local_scene_name}
    if studioMode:
        if currentPreviewScene == local_scene_name:
            await requestAsync("SetCurrentProgramScene", payload)
        else:
            await requestAsync("SetCurrentPreviewScene", payload)
    else:
        await requestAsync("SetCurrentProgramScene", payload)


async def toggle_mute_source(key):
    global data
    global ws
    local_source_name = data[key]["Name"]
    payload = {"source": local_source_name}
    await requestAsync("ToggleMute", payload)


async def toggle_studio_mode():
    # print("test 1")
    global studioMode
    print(studioMode)
    await requestAsync("SetStudioModeEnabled", {"studioModeEnabled":not studioMode})
    # print("Test")


async def toggle_render(key):
    global ws
    global source_render_data
    global data
    global currentScene

    local_source_name = data[key]["Name"]
    source_data = source_render_data[local_source_name]
    if source_data["current"]:
        if currentScene in source_data:
            new_state: bool = not source_data["scenes"][currentScene]
            await requestAsync("SetSceneItemRender", {"source": local_source_name, "render": new_state})
    else:
        new_state: bool = not source_data["state"]
        await ws.emit(Request("SetSceneItemRender",
                              {"scene-name": source_data["scene"], "source": local_source_name, "render": new_state}))


async def set_song_number():
    number: str = simpledialog.askstring("Gotteslob", "Bitte die Nummer im Gotteslob eintragen")
    Text = "Gotteslob: " + number.strip()
    await requestAsync("SetTextFreetype2Properties", {"source": "LiedText", "text": Text})
    await update_all_keys()


async def key_change_callback(local_deck, key, state):  # noqa
    global data
    key = str(key)
    if state:
        local_key_type = data.get(str(key), {"type": "none"})["type"]
        if local_key_type == "exit":
            await exit_async()
        elif local_key_type == "Scene":
            await switch_scene(key)
        elif local_key_type == "StudioMode":
            # print("Test 2")
            await toggle_studio_mode()
            # print("Test 3")
        elif local_key_type == "MuteSource":
            await toggle_mute_source(key)
        elif local_key_type == "SongNumber":
            await set_song_number()
        elif local_key_type == "Render" or local_key_type == "SongShow":
            await toggle_render(key)


atexit.register(exit_handler)


# Event Listeners
async def on_event(payload):
    print(payload)


async def on_source_mute_state_changed(payload):
    global muted_sources
    local_source_name = payload["sourceName"]
    muted = payload["muted"]
    if muted:
        muted_sources.add(local_source_name)
    else:
        muted_sources.discard(local_source_name)
    await update_all_keys()


async def on_switch_scenes(payload):
    global currentScene
    # old_key = scenes[currentScene]["key"]

    currentScene = payload["scene-name"]
    await update_all_keys()


async def on_studio_mode_change(payload):
    global studioMode
    global currentPreviewScene
    global currentScene
    studioMode = payload["new-state"]
    currentPreviewScene = currentScene
    # print(studioMode)
    await update_all_keys()


async def on_preview_scene_change(payload):
    global currentPreviewScene
    currentPreviewScene = payload["scene-name"]
    await update_all_keys()


async def on_on_scene_item_visibility_changed(payload):
    global source_render_data

    local_source_name: str = payload["item-name"]
    local_scene_name: str = payload["scene-name"]
    new_state: bool = payload["item-visible"]

    if local_source_name in source_render_data:
        if source_render_data[local_source_name]["current"]:
            source_render_data[local_source_name]["scenes"][local_scene_name] = new_state
        else:
            source_render_data[local_source_name]["state"] = new_state
    await update_all_keys()


async def requestAsync(request_name, payload=None):
    req = Request(request_name, payload)
    ret = await ws.call(req)
    if ret.ok():
        return ret.responseData
    else:
        print(ret.requestStatus)
        traceback.print_stack(limit=3)


def request(request_name, request_data=None):
    ret = loop.run_until_complete(ws.call(simpleobsws.Request(request_name, request_data)))
    if ret.ok():
        return ret.responseData
    else:
        raise AttributeError(ret.requestStatus)

def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    print(msg)
    loop.close()

if __name__ == "__main__":
    loop.set_exception_handler(handle_exception)

    ROOT = tk.Tk()
    ROOT.withdraw()

    with open("config.json") as f:
        data = json.load(f)

    ws = simpleobsws.WebSocketClient(password=data["obs_password"])

    tryConnect: bool = True

    while tryConnect:
        try:
            loop.run_until_complete(ws.connect())
            loop.run_until_complete(ws.wait_until_identified())
        except OSError as test:
            if '[Errno 111] Connect call failed' not in test.args[0]:
                raise test
        else:
            tryConnect = False

    deck.set_key_callback_async(key_change_callback)

    sceneList = request("GetSceneList")["scenes"]

    for i in range(0, deck.key_count()):
        key_type = data.get(str(i), {"type": "none"})["type"]
        if key_type == "Scene":
            scenes[data[str(i)]["Name"]] = {"key": i, "state": False}
        elif key_type == "Render" or key_type == "SongShow":
            source_name = data[str(i)].get("Name", "")
            scene_name = data[str(i)].get("scene", "")
            if scene_name == "":
                scene_data = {"": ""}
                for x in sceneList:
                    x = x["name"]
                    source_id = request(("GetSceneItemId", {"sceneName": x, "sourceName": source_name})).get(
                        "sceneItemId")
                    response = request("GetSceneItemEnabled", {"sceneName": x, "sceneItemId": source_id}).get(
                        "sceneItemEnabled", "error")
                    if not response == "error":
                        scene_data[x] = response
                source_render_data[source_name] = {"current": True, "scenes": scene_data}
            else:
                try:
                    source_id = request("GetSceneItemId", {"sceneName": scene_name, "sourceName": source_name})
                except:
                    source_id = None
                if not (source_id is None):
                    source_id = source_id.get("sceneItemId")
                    SourceInfo = request("GetSceneItemEnabled", {"sceneName": scene_name, "sceneItemId": source_id})
                    source_render_data[source_name] = {
                        "current": False, "scene": scene_name, "state": SourceInfo.get("sceneItemEnabled", False)}
                else:
                    source_render_data[source_name] = {"current": False, "scene": scene_name, "state": False}

    # get StudioMode
    studioMode = request("GetStudioModeEnabled")["studioModeEnabled"]
    if studioMode:
        currentPreviewScene = request("GetPreviewScene")["name"]

    # print(studioMode)
    # get current Scene
    currentScene = request("GetCurrentProgramScene")["currentProgramSceneName"]
    loop.run_until_complete(update_all_keys())
    #    ws.register(on_event)  # By not specifying an event to listen to, all events are sent to this callback.
    ws.register_event_callback(on_switch_scenes, 'SwitchScenes')
    ws.register_event_callback(on_studio_mode_change, "StudioModeSwitched")
    ws.register_event_callback(on_preview_scene_change, "PreviewSceneChanged")
    ws.register_event_callback(on_source_mute_state_changed, "SourceMuteStateChanged")
    ws.register_event_callback(on_on_scene_item_visibility_changed, "SceneItemVisibilityChanged")

    loop.run_forever()
