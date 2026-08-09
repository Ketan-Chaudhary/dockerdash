name: Bug Report
description: Create a report to help us fix a bug or unexpected behavior in DockDash
title: '[BUG]: '
labels: ['bug']
body:
  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: A clear and concise description of what the bug is.
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: Steps to reproduce the behavior.
      placeholder: |
        1. Open DockDash
        2. Press 'l' on container
        3. See error...
    validations:
      required: true
  - type: input
    id: os
    attributes:
      label: Operating System
      placeholder: e.g. Arch Linux / Ubuntu 24.04 / Windows 11 / macOS Sequoia
    validations:
      required: true
