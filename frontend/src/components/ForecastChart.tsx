import { useState } from "react";
import { Pressable, View } from "react-native";
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from "react-native-svg";

import type { ForecastPoint } from "../api";
import { compact, dayMonth, myr } from "../format";
import { colors, fonts } from "../theme";

const AXIS_WIDTH = 44;
const LABEL_HEIGHT = 28;
const STEP = 20000;

/**
 * 13-week closing-balance line. `comparison` draws a dashed scenario line; the
 * highlighted week gets a bold label (amber when negative) and optionally a band.
 */
export function ForecastChart({
  points,
  comparison,
  highlight,
  band = false,
  onSelect,
  height = 148,
}: {
  points: ForecastPoint[];
  comparison?: ForecastPoint[];
  highlight?: string | null;
  band?: boolean;
  onSelect?: (weekOf: string) => void;
  height?: number;
}) {
  const [width, setWidth] = useState(0);
  const values = [...points, ...(comparison ?? [])].map((point) => point.closing_balance);
  const topTick = Math.max(STEP, Math.floor(Math.max(...values) / STEP) * STEP);
  const ticks = Array.from({ length: topTick / STEP + 1 }, (_, index) => index * STEP);
  const domainMax = Math.max(...values, topTick);
  const domainMin = Math.min(0, ...values);

  const plotTop = 8;
  const plotBottom = height - LABEL_HEIGHT;
  const plotLeft = AXIS_WIDTH;
  const plotRight = width - 24;
  const spacing = (plotRight - plotLeft) / (points.length - 1);
  const x = (index: number) => plotLeft + index * spacing;
  const y = (value: number) =>
    plotTop + ((domainMax - value) / (domainMax - domainMin)) * (plotBottom - plotTop);
  const path = (series: ForecastPoint[]) =>
    series.map((point, index) => `${index ? "L" : "M"}${x(index)},${y(point.closing_balance)}`).join(" ");

  const highlightIndex = points.findIndex((point) => point.week_of === highlight);
  const highlightNegative = highlightIndex >= 0 && points[highlightIndex].closing_balance < 0;

  return (
    <View onLayout={(event) => setWidth(event.nativeEvent.layout.width)} style={{ height }}>
      {width > 0 && (
        <Svg width={width} height={height}>
          {band && highlightIndex >= 0 && (
            <Rect
              x={x(highlightIndex) - 18}
              y={plotTop - 8}
              width={36}
              height={plotBottom - plotTop + 16}
              rx={6}
              fill={highlightNegative ? colors.warningSurface : colors.jade}
            />
          )}
          {ticks.map((tick) => (
            <Line
              key={tick}
              x1={plotLeft}
              x2={plotRight}
              y1={y(tick)}
              y2={y(tick)}
              stroke={tick === 0 ? colors.axis : colors.edge}
              strokeWidth={1}
            />
          ))}
          {ticks.map((tick) => (
            <SvgText
              key={`label-${tick}`}
              x={plotLeft - 10}
              y={y(tick) + 4}
              fontSize={11}
              fontFamily={fonts.regular}
              fill={colors.secondary}
              textAnchor="end"
            >
              {compact(tick)}
            </SvgText>
          ))}
          {comparison && (
            <Path d={path(comparison)} stroke={colors.sage} strokeWidth={2} strokeDasharray="5 5" fill="none" />
          )}
          <Path d={path(points)} stroke={colors.emerald} strokeWidth={2} fill="none" strokeLinejoin="round" />
          <Circle cx={x(0)} cy={y(points[0].closing_balance)} r={3.5} fill={colors.emerald} />
          {onSelect && highlightIndex > 0 && (
            <Circle
              cx={x(highlightIndex)}
              cy={y(points[highlightIndex].closing_balance)}
              r={4}
              fill={colors.porcelain}
              stroke={highlightNegative ? colors.warning : colors.emerald}
              strokeWidth={2}
            />
          )}
          {points.map((point, index) => {
            const active = index === highlightIndex;
            return (
              <SvgText
                key={point.week_of}
                x={x(index)}
                y={height - 6}
                fontSize={11}
                fontFamily={active ? fonts.semibold : fonts.regular}
                fill={active ? (highlightNegative ? colors.warning : colors.emerald) : colors.secondary}
                textAnchor="middle"
              >
                {index === 0 ? "Today" : dayMonth(point.week_of)}
              </SvgText>
            );
          })}
        </Svg>
      )}
      {width > 0 &&
        onSelect &&
        points.slice(1).map((point, offset) => (
          <Pressable
            key={point.week_of}
            onPress={() => onSelect(point.week_of)}
            accessibilityLabel={`Week of ${dayMonth(point.week_of)}, closing ${myr(point.closing_balance)}`}
            style={{ position: "absolute", top: 0, bottom: 0, left: x(offset + 1) - spacing / 2, width: spacing }}
          />
        ))}
    </View>
  );
}
