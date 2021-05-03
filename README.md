# pygapa
**pygapa** (short for *Python Galaxy Particles*) is a Python tool for editing particle and effect data in *Super Mario Galaxy 1 & 2*. It can convert the files from *Effect.arc* into editable JSON files and dumps textures as BTI files. The extracted and edited files can then be converted back into *Super Mario Galaxy*'s format.

# Requirements
Before you can use this tool, make sure you have installed and prepared the following programs and software:
- [Python 3.7.0](https://www.python.org/) or newer
- Tools to extract and pack RARC archives, like [szstools](http://amnoid.de/gc/)
- Text editor, for example [Notepad++](https://notepad-plus-plus.org/downloads/)

# Converting files
If you want to dump and convert particle data, you need to extract the files from *ParticleData/Effect.arc* first. You can use *szstools* to deal with RARC archives. The extracted files are *Particles.jpc*, *ParticleNames.bcsv* and *AutoEffectList.bcsv*. Copy that folder's path and open your command prompt, shell or any command-line console. In the shell, browse to the *pygapa* folder and type in the following command:
``python pygapa.py dump <path to JPC and BCSV files> <path to dump files to>``
Then, hit enter and *pygapa* will dump the data for you. This may take a couple of seconds. Any non-existent folders will be created by the tool if they don't exist already.

Converting the JSON and BTI files back into SMG's format is very simple as well. Again, in the shell, just enter the following command:
``python pygapa.py pack <path to JSON and BTI files> <path to JPC and BCSV files>``
You'll then obtain new BCSV and JPC files that can be packed into a proper Effect.arc archive using *szstools*.

# Files
After dumping the files, you'll find the following files and folders:
- **Particles.json**: Specifies the particle and texture names that belong to the JPC file.
- **Effects.json**: A simplified version of *AutoEffectList*, the table that specifies every object's effects.
- **Particles**: Contains JSON files for every particle.
- **Textures**: Contains BTI particle textures.

## Particles.json
This file specifies the particles and textures that should be packed into the JPC file. If you are adding new textures or particles, make sure to add them to the respective lists here. You can also delete entries to exclude them from the JPC. *Particles.json* has a very simple structure and looks like this:
```json
{
	"particles": [
		"2PGlowActiveLoop00",
		"AirBubbleGeneratorShoot00",
		"AirBubbleGeneratorShoot01",
		...
		"testFooFiterSpray02"
	],
	"textures": [
		"mr_glow01_i",
		"mr_flash00_i",
		"mr_sand00_ia",
		...
		"DashYoshiBlur"
	]
}
```

## Effects.json
As pointed out above, this file contains the entries from *AutoEffectList.bcsv*. Here, you define all effects for  objects and the particles they use. There are quite a lot of fields here, but for the sake of simplicity, the tool drops any attributes containing default values. The structure looks like this (example from SMG1):
```json
[
    {
        "GroupName": "Kuribo",
        "AnimName": "Run",
        "UniqueName": "DashAttrDefault",
        "EffectName": [
            "SmokeSphere"
        ],
        "JointName": "Center",
        "OffsetY": -35.0,
        "Affect": "T/R",
        "Follow": "T",
        "ScaleValue": 0.3,
        "DrawOrder": "3D"
    },
    ...
]
```
Each entry consists of these attributes. When packing the files again, the default values are used whenever an attribute cannot be found.
| Field | Type | Default | Description |
| - | - | - | - |
| GroupName | string | **Required** | The object's name to which the effect belongs. |
| AnimName | string | *(empty)* | Animation name onto during which the effect is used. |
| ContinueAnimEnd | bool | false | Declares whether the effect continues after the animation has ended. |
| UniqueName | string | **Required** | A unique identifier for the effect in the goup. |
| EffectName | string[]| **Required** | A list of particle effects to be used. |
| ParentName | string | *(empty)* | Unknown. |
| JointName | string | *(empty)* | The model's joint to which the effect is attached. |
| OffsetX | float | 0.0 | X offset from the object/joint's position. |
| OffsetY | float | 0.0 | Y offset from the object/joint's position. |
| OffsetZ | float | 0.0 | Z offset from the object/joint's position. |
| StartFrame | int | 0 | The frame on which the effect starts to appear. |
| EndFrame | int | -1 | If set to a positive value, this defines the life span in frames. |
| Affect | string | *(empty)* | Unknown. Slash-separated list of *T*, *R* and/or *S*. |
| Follow | string | *(empty)* | Unknown. Slash-separated list of *T*, *R* and/or *S*. |
| ScaleValue | float | 1.0 | Scaling/size factor. |
| RateValue | float | 1.0 | Unknown. |
| PrmColor | string | *(empty)* | Primary color value. (e.g. *#ff0000* is R = 255, G = 0 B = 0) |
| EnvColor | string | *(empty)* | Environment color value. (e.g. *#00ff00* is R = 0, G = 255, B = 0) |
| LightAffectValue | float | 0.0 | Unknown. |
| DrawOrder | string | *(empty)* | Rendering order/priority, see below for allowed values. |

### DrawOrder types
The DrawOrder field declares the rendering order or priority.

| Type | Priority |
| - | - |
| 3D | 0 |
| PAUSE_IGNORE | 1 |
| INDIRECT | 2 |
| AFTER_INDIRECT | 3 |
| BLOOM_EFFECT | 4 |
| AFTER_IMAGE_EFFECT | 5 |
| 2D | 6 |
| 2D_PAUSE_IGNORE | 7 |
| FOR_2D_MODEL | 8 |

## Particle files
JSON files for every particle can be found in the *Particles* folder. At the moment, not much is documented about particle data, so for most of the blocks a hex string containing the raw bytes is used. Here is an example from *AirBubbleGeneratorShoot00.json*. The raw hex bytes have been replaced with "..." here.
```json
{
    "unk4": 256,
    "unk6": 256,
    "dynamicsBlock": "...",
    "fieldBlocks": [
        "..."
    ],
    "baseShape": "...",
    "extraShape": "...",
    "textures": [
        "mr_sand00_ia",
        "mr_glow01_i"
    ]
}
```
Each particle entry has the same structure, but some fields are optional:

| Field | Type | Description |
| - | - | - |
| unk4 | short(?) | Unknown. |
| unk6 | short(?) | Unknown. |
| dynamicsBlock | JPADynamicsBlock | Required and unknown. |
| fieldBlocks | JPAFieldBlock[] | Optional and unknown. There may be more than one. |
| keyBlocks | JPAKeyBlock[] | Optional and unknown. There may be more than one. |
| baseShape | JPABaseShape | Required and unknown. |
| extraShape | JPAExtraShape | Required and unknown. |
| childShape | JPAChildShape | Optional and unknown. |
| exTexShape | JPAExTexShape | Optional and unknown. |
| textures | string[] | List of textures to be used. Required. |

# How to contribute
You can help document the particle structure since none of these blocks are properly documented yet.
