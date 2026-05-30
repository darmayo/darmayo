name: Generate Custom GitHub Dashboard

on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch:
  push:
    branches:
      - main

permissions:
  contents: write

jobs:
  dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate custom dashboard SVG
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/generate_dashboard.py

      - name: Commit dashboard
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: update custom github dashboard
          file_pattern: github-dashboard.svg
