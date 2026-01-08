from database import insert_game

data = {
  "id": "pokemon_unbound",
  "title": "Pokémon Unbound",
  "console": "gba",
  "version": "2.1.1",
  "release_date": "2024-04-14",
  "author": "Skeli",
  "description": "A story-driven FireRed ROM hack set in the Borrius region. Features Gen 1-7 Pokémon, Gen 8 battle engine, complex puzzles, and post-game content. Choose from Easy to Insane difficulty modes with dynamic AI.",
  "base_game": "Pokémon FireRed",
  "version_region": "USA",
  "dev_stage": "complete",
  "features": [
    "Gen 1-7 Pokémon",
    "Gen 8 Battle Engine",
    "Dynamic AI (4 Difficulty Modes)",
    "QoL Features (Unlimited Bag, Auto-Run, DexNav)",
    "80+ Missions",
    "Character Customization (300+ Combinations)",
    "Gen 4 Overworld Graphics",
    "Gen 5-esque Interfaces",
    "Day & Night System",
    "New HM System (ADM)",
    "Mega Evolution",
    "Dynamax & Gigantamax",
    "Z-Moves",
    "Battle Facilities",
    "Safari Zone Mini-games",
    "Cloud Burst Mini-game",
    "Safari Sniper Mini-game",
    "Underground Mining",
    "180+ Original Soundtrack"
  ],
  "image_url": "https://i.imgur.com/HMT9q3Z.png",
  "screenshots": [
    "https://i.imgur.com/OUWXtD0.png",
    "https://i.imgur.com/SEBRdPG.png",
    "https://i.imgur.com/IILcQLr.png",
    "https://i.imgur.com/yxnDnr4.png",
    "https://i.imgur.com/JcHbIKH.png",
    "https://i.imgur.com/1oTkbq6.png",
    "https://i.imgur.com/LnStzst.png",
    "https://i.imgur.com/uOUEa1B.png"
  ],
  "download_link": "https://www.mediafire.com/file/aw7l6x0x84otsye/Pokemon+Unbound+Patch+2.1.1.zip/file",
  "popular": True,
  "online_play": False,
  "instruction": True,
  "instruction_text": "Requires a Pokémon FireRed USA v1.0 ROM. Patch using UPS or IPS format patcher. Supports headered and unheadered ROMs. Recommended emulators: mGBA, Visual Boy Advance, or hardware via flash cartridge.",
  "discord_url": "https://discord.gg/k34Jm4T",
  "reddit_url": "",
  "support_forum_url": "https://www.pokecommunity.com/threads/pokémon-unbound-completed.382178/",
  "troubleshooting_url": "https://docs.google.com/spreadsheets/d/1LFSBZuPDtJrwAz7t6ZkJ-il4j8M3qCdaKLNe6EZdPmQ/edit",
  "base_region": "USA",
  "base_revision": "v1.0",
  "base_header": "Headered or Unheadered",
  "patch_format": "ups",
  "patch_output_ext": ".gba",
  "instructions_pc": "1. Get a legal Pokémon FireRed USA v1.0 ROM\n2. Download the Pokémon Unbound patch\n3. Use a UPS patcher (mGBA, Floating IPS, etc.)\n4. Apply the patch to your ROM\n5. Load in your favorite emulator or flash cartridge",
  "instructions_android": "1. Download the patch on your Android device\n2. Use an app like UniPatcher or Floating IPS\n3. Select the Pokémon Unbound patch\n4. Select your FireRed ROM file\n5. Apply the patch\n6. Load in mGBA or another GBA emulator"
}

if __name__ == "__main__":
    try:
        game_id = insert_game(data)
        print(f"Successfully inserted game: {game_id}")
    except Exception as e:
        print(f"Error inserting game: {e}")
