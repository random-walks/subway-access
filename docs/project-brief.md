# Project Brief

## Problem

Subway accessibility is usually communicated as a station attribute, but riders experience it as a reliability and routing problem. A station that is technically accessible but frequently out of service is not solving the same problem as a consistently usable step-free path.

## Intended Users

- accessibility advocates
- planners
- city and transit policy staff
- journalists
- urban researchers

## Product Shape

`subway-access` should become a reusable Python package that:

1. ingests official accessibility and outage data
2. combines it with pedestrian catchments and demographics
3. produces transparent scores, maps, and tables

## Why This Is Worth Building

There is prior civic-tech work and useful raw data in this space, but there is not an obvious actively maintained package that packages reliability-aware accessibility analysis into a reproducible analyst workflow.

## Positioning

Do not position this as a trip planner.

Position it as a transparent accessibility analysis toolkit for answering questions like:

- which neighborhoods have weak access to reliable accessible stations
- which stations matter most for equity
- where outage patterns create the biggest real-world accessibility gaps
