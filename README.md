# See No Evil: Semantic Context-Aware Privacy Risk Detection for AR

This repository contains the official implementation of the paper **"SEE NO EVIL: SEMANTIC CONTEXT-AWARE PRIVACY RISK DETECTION FOR AR"** (Accepted by **ICASSP 2026**).

**PrivAR** is a privacy-preserving framework designed for Augmented Reality (AR) systems. It addresses the "always-on" sensing privacy risks by leveraging Vision Language Models (VLMs) with Chain-of-Thought (CoT) prompting.

### Key Features:
* **Context-Aware Risk Detection:** Uses visual scene cues to infer potential sensitive information (e.g., identifying password notes in an office setting) rather than relying solely on object categories.
* **Privacy-Preserving Obfuscation:** Implements a "text obfuscation first" pipeline at the edge server using the EAST text detection model and a combination of Gaussian blur and elastic deformation. This prevents the VLM provider from accessing raw sensitive text.
* **Warning Interfaces:** Provides contextually-informed warning modes (Center-screen, Top-screen, Region Overlay) to enhance user privacy awareness in AR.


This project was built based on unity's template of AR mobile, and used the editor version of unity: 2022.3.6f1.
