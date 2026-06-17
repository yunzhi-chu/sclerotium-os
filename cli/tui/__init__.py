"""Sclerotium OS — Claude Code-equivalent Textual Terminal UI.

Replicates Claude Code's React+Ink terminal experience using Python's Textual framework:
  - ChatScreen: streaming markdown, tool-use widgets, virtual scrolling
  - DashboardScreen: FCPI gauges, event log, genome tree
  - PermissionDialog: interactive approval screens
  - StatusBar: token count, cost, model info

Architecture:
  Claude Code: React + Ink (custom fork) + Yoga CSS + Chalk
  Sclerotium:  Textual (CSS layout) + Rich (coloring)
"""
