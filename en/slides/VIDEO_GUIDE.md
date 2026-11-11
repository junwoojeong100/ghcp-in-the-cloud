# Recording the demo videos and inserting them into the PPTX

## Goal and current state

This guide describes how to record the demos you ran for real on GitHub and Azure as six independent videos, and how to put those videos into the presentation slides. `en/slides/` has no recordings, and it contains no screens captured from a real GitHub organization or Azure subscription. The generated PPTX therefore shows a note about where to record, in place of each video. The videos play only after you run the demos for real and add the files.

The click path, the commands and the success criteria of each demo follow the linked demo guides. The speaker script and the recording cues are also in the speaker notes of the PPTX.

## What is already recorded, and recording again

The English and Korean recordings are not in `slides/` or `en/slides/`. They are in the release `recorded-demo-slides`: a 45-slide deck with 32 videos embedded in each language, also published on GitHub Pages, and the full English video (about 24 minutes) as `ghcp-in-the-cloud-demo-en.mp4` ([Slides and guides](../README.md#slides-and-guides)).

The recordings were made with an automatic recording script that is not in this repository and is not published. The script points at the practice repositories that no longer exist (`ghcp-in-the-cloud-practice` and `ghcp-in-the-cloud-practice-en`). To record again, [create a new practice repository from the template](../README.md#source-repository-and-practice-repositories) and change the repository name in the script to the new name.

## Before you record

1. Set up the demo environment by following `README.md` at the repository root and the guide of the demo you will film, and rehearse the whole sequence once. Before you create GitHub or Azure resources and deploy, check the permissions, the cost and the cleanup steps in each guide.
2. Prepare a browser profile and a terminal for the presentation, and turn off notifications. Set the screen scale and the font size so that they are easy to read.
3. Make sure that no real credentials or personal information appear on screen, in audio or in notifications. Do not show or say `DEMO_PASSWORD`, tokens, `Authorization` headers, keys, secret values or sensitive resource identifiers. Review the whole screen and the audio of the recorded file again before you use it in a presentation.
4. In the screen recorder, select the whole 16:9 screen and the microphone. When you edit, do not cut the demo actions and the success criteria. Keep the waiting parts short, but do not replace or embellish the real result.

## Recording plan for each demo

| File | Flow to capture on screen | Success screen | Guide |
|---|---|---|---|
| `copilot.mp4` | Settings files → assign the issue → agent session, PR and CI → Copilot review and the human merge | The real PR changes, the checks that passed, the review, and the result a person approved | [Demo 1](../demos/01-github-copilot/README.md). Start the agent work in advance to cut the waiting time. |
| `repo.mp4` | Codespaces tests → Rulesets and CODEOWNERS → the checks on a deliberately risky PR → Dependabot | The active ruleset and security checks blocking the PR | [Demo 2](../demos/02-github-repo/README.md). Use a practice repository and do not merge the risky PR. |
| `actions.mp4` | Parallel CI on a PR → a setup with no stored Actions secrets → the approval gate and the OIDC deployment | Passing CI, the approval step, and the successful result of a real deployment run | [Demo 3](../demos/03-github-actions/README.md). Run the Azure deployment scene on a real subscription and do not show credentials on screen. |
| `foundry.mp4` | Check the gpt-6.1-sol deployment → a real call with Entra ID → check `/api/info` | The `backend`, `auth`, `model` and `effort` values and the app's answer | [Demo 4](../demos/04-microsoft-foundry/README.md). Use the keyless authentication flow of the guide, not an API key. |
| `aca.mp4` | Confirm zero replicas → wake it with a request → revision canary and rollback → load-based scale-out | The real Container Apps revision and replica state and the app's responses | [Demo 5](../demos/05-azure-container-apps/README.md). Propagation and start-up waits vary by environment. |
| `aks.mp4` | Pods and HPA → rolling update and rollback → Workload Identity → the Pod Security rejection check | Ready pods, the real rollout result, and the secretless identity setup | [Demo 6](../demos/06-aks/README.md). For the failure scene, use only the safe rejection test given in the guide. |

## Putting them into the PPTX

1. In the repository root, create the `en/slides/videos/` folder and save the files of the table above under those names. The videos must be MP4, and you must not change the names.
2. Run `python en/slides/build_deck.py`. For every demo that has a video, a separate playback slide is created in the order value, demo flow, video, key code. If a file is missing, the slide keeps a note with the file path.
3. Open the generated `en/slides/demo-presentation-en.pptx` in PowerPoint and check each video's playback, aspect ratio and sound, and whether any subtitle or sensitive information is exposed. Manage the generated file according to the repository's policy for large files.

If you have not recorded real videos, do not present a mock response or a still image as if it were the result of a real GitHub or Azure run. If you need an offline mock video, state clearly in the video title and the description that it is in mock mode.
