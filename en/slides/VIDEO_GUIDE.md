# Recording the demo videos and publishing the 45-slide deck

## Goal and current state

The current presentation is the [45-slide recorded-demo deck](README.md) with 32 embedded videos. This guide describes how to record the demos again, replace videos in the repository PPTX files, and publish them to GitHub Pages.

The click path, commands and success criteria of each demo follow the linked demo guides. The PPTX sources are managed in the repository; the full English MP4 is a separate release asset.

## What is already recorded, and recording again

The Korean deck is [`slides/GHCP_in_the_Cloud_Demo_KO.pptx`](../../slides/GHCP_in_the_Cloud_Demo_KO.pptx), and the English deck is [`en/slides/GHCP_in_the_Cloud_Demo_EN.pptx`](GHCP_in_the_Cloud_Demo_EN.pptx). Each has 45 slides and 32 embedded videos, and cloning the repository includes both ([Slides and guides](../README.md#slides-and-guides)). The full English video, `ghcp-in-the-cloud-demo-en.mp4` (about 24 minutes), remains in the release `recorded-demo-slides` and plays on the [English web page](https://junwoojeong100.github.io/ghcp-in-the-cloud/en/).

The recording automation is not in this repository, and the old practice repositories were deleted. To record again, [create a new practice repository from the template](../README.md#source-repository-and-practice-repositories), run each demo following its guide, and capture it with a screen recorder.

## Before you record

1. Set up the demo environment by following `README.md` at the repository root and the guide of the demo you will film, and rehearse the whole sequence once. Before you create GitHub or Azure resources and deploy, check the permissions, the cost and the cleanup steps in each guide.
2. Prepare a browser profile and a terminal for the presentation, and turn off notifications. Set the screen scale and the font size so that they are easy to read.
3. Make sure that no real credentials or personal information appear on screen, in audio or in notifications. Do not show or say `DEMO_PASSWORD`, tokens, `Authorization` headers, keys, secret values or sensitive resource identifiers. Review the whole screen and the audio of the recorded file again before you use it in a presentation.
4. In the screen recorder, select the whole 16:9 screen and the microphone. When you edit, do not cut the demo actions and the success criteria. Keep the waiting parts short, but do not replace or embellish the real result.

## Recording plan for each demo

| Demo | Flow to capture on screen | Success screen | Guide |
|---|---|---|---|
| GitHub Copilot | Settings files → assign the issue → agent session, PR and CI → Copilot review and the human merge | The real PR changes, the checks that passed, the review, and the result a person approved | [Demo 1](../demos/01-github-copilot/README.md). Start the agent work in advance to cut the waiting time. |
| GitHub Repo | Codespaces tests → Rulesets and CODEOWNERS → the checks on a deliberately risky PR → Dependabot | The active ruleset and security checks blocking the PR | [Demo 2](../demos/02-github-repo/README.md). Use a practice repository and do not merge the risky PR. |
| GitHub Actions | Parallel CI on a PR → a setup with no stored Actions secrets → the approval gate and the OIDC deployment | Passing CI, the approval step, and the successful result of a real deployment run | [Demo 3](../demos/03-github-actions/README.md). Run the Azure deployment scene on a real subscription and do not show credentials on screen. |
| Microsoft Foundry | Check the gpt-6.1-sol deployment → a real call with Entra ID → check `/api/info` | The `backend`, `auth`, `model` and `effort` values and the app's answer | [Demo 4](../demos/04-microsoft-foundry/README.md). Use the keyless authentication flow of the guide, not an API key. |
| Azure Container Apps | Confirm zero replicas → wake it with a request → revision canary and rollback → load-based scale-out | The real Container Apps revision and replica state and the app's responses | [Demo 5](../demos/05-azure-container-apps/README.md). Propagation and start-up waits vary by environment. |
| AKS | Pods and HPA → rolling update and rollback → Workload Identity → the Pod Security rejection check | Ready pods, the real rollout result, and the secretless identity setup | [Demo 6](../demos/06-aks/README.md). For the failure scene, use only the safe rejection test given in the guide. |

## Updating and publishing the PPTX

1. Open `en/slides/GHCP_in_the_Cloud_Demo_EN.pptx` in PowerPoint and edit the content and videos you need. For the Korean edition, use `slides/GHCP_in_the_Cloud_Demo_KO.pptx` (see the [Korean guide](../../slides/VIDEO_GUIDE_KO.md)).
2. Check the 45-slide structure and playback of all 32 videos, their aspect ratio, sound, captions and any exposed sensitive information. Keep the file names and locations, and update the English deck when the Korean content changes.
3. Include the edited PPTX files in a PR. After human review and merge to `main`, `Pages` copies both repository decks to the site root and publishes them automatically. No separate PPTX upload to the release is needed.
4. After the `Pages` workflow succeeds, open or download the PPTX from the [web page](https://junwoojeong100.github.io/ghcp-in-the-cloud/en/) and verify the changes and video playback.

When replacing only the full English MP4, replace that asset in the release `recorded-demo-slides`, then publish again with **Actions → Pages → Run workflow**. The PPTX distribution copies left in the release are not updated automatically; use the repository and GitHub Pages for the latest decks.

If you have not recorded real videos, do not present a mock response or a still image as if it were the result of a real GitHub or Azure run. If you need an offline mock video, state clearly in the video title and the description that it is in mock mode.
