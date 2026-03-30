# Original Spec Notes

## One-Liner

Spatial analysis toolkit that measures how accessible NYC's subway system actually is by combining ADA station data, outage feeds, catchments, and demographics into equity-focused accessibility scores.

## Core Idea

The package should help answer not just whether a station is accessible, but whether nearby residents have reliable accessible transit in practice.

## Expected Library Surface

- data ingestors for MTA, Census, and street-network inputs
- catchment generation
- accessibility scoring
- gap analysis
- outputs for maps, CSVs, and notebooks

## Key Technical Choices

- use network-based catchments when possible
- track outage reliability over time
- weight accessibility by neighborhood need
- keep dependencies open and reproducible

## Intended Showcase Value

This project is meant to demonstrate:

- spatial analysis for policy and equity
- multi-source public data integration
- transit domain understanding
- public-facing analytical tooling rather than a one-off study
