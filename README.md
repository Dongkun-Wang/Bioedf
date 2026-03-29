<p align="center">
  <img src=".github/assets/bioedf-banner.svg" alt="Bioedf banner" width="100%" />
</p>

<p align="center">
  <a href="README_CN.md"><strong>中文文档</strong></a>
  ·
  <a href="README_EN.md"><strong>English</strong></a>
</p>

<p align="center">
  <a href="README_CN.md"><img src="https://img.shields.io/badge/Docs-%E4%B8%AD%E6%96%87-1E7C72?style=flat-square" alt="Chinese Docs" /></a>
  <a href="README_EN.md"><img src="https://img.shields.io/badge/Docs-English-D98A57?style=flat-square" alt="English Docs" /></a>
  <img src="https://img.shields.io/badge/Python-3.12+-4B9AA6?style=flat-square" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/Format-EDF-5E8E73?style=flat-square" alt="EDF" />
</p>

<p align="center">
  Bioedf is a local EDF biosignal analysis toolkit for EEG, ECG, and EMG, with both CLI and web UI workflows.
  <br/>
  Bioedf 是一个面向 EEG、ECG、EMG 的本地 EDF 生理信号分析工具，支持命令行与前端页面两种使用方式。
</p>

## Overview

- EEG, ECG, EMG EDF analysis in one project
- Local web frontend for upload, module selection, and result review
- EDF-aware channel handling:
  - EEG: one EDF contains five channels and is averaged before analysis
  - ECG: if multi-channel, channel 3 is analyzed by default
  - EMG: available channels are analyzed directly
- Built-in preprocessing, segmentation, plotting, and result export

## Choose Your Guide

- 中文说明: [README_CN.md](README_CN.md)
- English guide: [README_EN.md](README_EN.md)

## Repository

```bash
git clone git@github.com:Dongkun-Wang/Bioedf.git Bioedf
cd Bioedf
```
