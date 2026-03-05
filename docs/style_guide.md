# Budget App UI Style Guide

## Overview

This document defines the visual design system for the Budget App. The
goal is a clean, data‑focused financial dashboard using a dark grey
theme that reduces eye strain and makes charts easy to read.

Design principles:

-   Calm and analytical
-   Low visual noise
-   Strong emphasis on financial numbers
-   High readability for charts and tables
-   Consistent color semantics for financial meaning

------------------------------------------------------------------------

# Color System

## Background Layers

  Token              Color     Usage
  ------------------ --------- ------------------------
  --bg-main          #2F2F2F   Application background
  --bg-card          #3A3A3A   Cards and panels
  --bg-card-hover    #444444   Hover state
  --border-default   #505050   Dividers and borders

------------------------------------------------------------------------

## Text Colors

  Token              Color     Usage
  ------------------ --------- -----------
  --text-primary     #F2F2F2   Main text
  --text-secondary   #C8C8C8   Labels
  --text-muted       #9A9A9A   Metadata

------------------------------------------------------------------------

## Financial Semantic Colors

These colors represent financial meaning and must be used consistently.

  Meaning              Token             Color
  -------------------- ----------------- ---------
  Income / Positive    --color-income    #3FB950
  Expense / Negative   --color-expense   #F85149
  Budget / Neutral     --color-budget    #58A6FF
  Warning              --color-warning   #F2CC60

Rules:

-   Green = income only
-   Red = expenses only
-   Do not use these colors for decoration

------------------------------------------------------------------------

# Chart Color Palette

Used for category breakdowns and multi‑series charts.

    #58A6FF
    #3FB950
    #F2CC60
    #A371F7
    #FF7B72
    #79C0FF
    #D2A8FF

Chart guidelines:

-   Gridlines: #404040
-   Axis labels: #9A9A9A
-   Chart background: transparent
-   Avoid pure white lines

------------------------------------------------------------------------

# Layout System

The application uses a card‑based dashboard layout.

Example structure:

    Dashboard
     ├ Net Worth Card
     ├ Monthly Cash Flow Chart
     ├ Spend vs Budget Chart
     ├ Recent Transactions Table
     └ Category Breakdown Chart

------------------------------------------------------------------------

# Card Design

Cards contain charts, tables, or financial summaries.

    background: #3A3A3A
    border: 1px solid #505050
    border-radius: 8px
    padding: 16px

Recommended spacing:

    Card gap: 24px
    Internal padding: 16px
    Section spacing: 32px

------------------------------------------------------------------------

# Buttons

## Primary Button

Used for main actions.

    background: #58A6FF
    color: white
    border-radius: 6px
    padding: 8px 14px

Hover:

    background: #6CB6FF

------------------------------------------------------------------------

## Secondary Button

Used for less important actions.

    background: #3A3A3A
    border: 1px solid #505050
    color: #F2F2F2

------------------------------------------------------------------------

# Tables

Tables are used for transaction history.

Background:

    #3A3A3A

Header style:

    text: #C8C8C8
    border-bottom: #505050

Row hover:

    #444444

Financial values:

    Income → #3FB950
    Expense → #F85149

------------------------------------------------------------------------

# Typography

Numbers are the most important visual element in a finance app.

Recommended fonts:

Primary UI font:

    Inter

Numeric font (optional):

    JetBrains Mono

Font sizes:

  Element            Size
  ------------------ ------
  Dashboard number   32px
  Card title         16px
  Table text         14px
  Labels             12px

------------------------------------------------------------------------

# Dashboard Layout

Recommended default dashboard layout.

    -------------------------------------------------
     Net Worth            | Monthly Cash Flow
    -------------------------------------------------

     Spend vs Budget (chart)

    -------------------------------------------------

     Recent Transactions  | Category Breakdown
    -------------------------------------------------

------------------------------------------------------------------------

# UI Token Example (CSS Variables)

``` css
:root {

  --bg-main: #2F2F2F;
  --bg-card: #3A3A3A;
  --bg-card-hover: #444444;

  --border-default: #505050;

  --text-primary: #F2F2F2;
  --text-secondary: #C8C8C8;
  --text-muted: #9A9A9A;

  --color-income: #3FB950;
  --color-expense: #F85149;
  --color-budget: #58A6FF;
  --color-warning: #F2CC60;

}
```

------------------------------------------------------------------------

# Design Rules

1.  Avoid visual clutter
2.  Use cards for content grouping
3.  Financial numbers should stand out
4.  Charts should prioritize readability
5.  Maintain consistent spacing and colors

------------------------------------------------------------------------

# Future UI Enhancements

Possible future improvements:

-   Dark / light theme toggle
-   Animated charts
-   Interactive category drilldowns
-   Advanced financial trend visualizations
