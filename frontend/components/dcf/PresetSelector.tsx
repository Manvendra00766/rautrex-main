"use client"

import React, { useState } from 'react'
import { PRESETS, PresetKey, Preset } from '@/lib/dcf_presets'
import { DCFInput } from '@/types/dcf'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

interface PresetSelectorProps {
  onApply: (values: Partial<DCFInput>) => void
}

export default function PresetSelector({ onApply }: PresetSelectorProps) {
  const [activePreset, setActivePreset] = useState<PresetKey | null>(null)

  const handleSelect = (key: PresetKey) => {
    if (activePreset === key) {
      setActivePreset(null)
    } else {
      setActivePreset(key)
      onApply(PRESETS[key].values)
    }
  }

  const getColorClasses = (color: string, isActive: boolean) => {
    switch (color) {
      case 'yellow':
        return isActive 
          ? 'border-yellow-400 bg-yellow-400/10' 
          : 'border-white/5 hover:border-yellow-400/50'
      case 'blue':
        return isActive 
          ? 'border-blue-500 bg-blue-500/10' 
          : 'border-white/5 hover:border-blue-500/50'
      case 'green':
        return isActive 
          ? 'border-green-500 bg-green-500/10' 
          : 'border-white/5 hover:border-green-500/50'
      default:
        return 'border-white/5'
    }
  }

  const getBorderColor = (color: string) => {
    switch (color) {
      case 'yellow': return 'bg-yellow-400'
      case 'blue': return 'bg-blue-500'
      case 'green': return 'bg-green-500'
      default: return 'bg-white/10'
    }
  }

  return (
    <div className="flex flex-wrap gap-3 w-full">
      {(Object.entries(PRESETS) as [PresetKey, Preset][]).map(([key, preset]) => {
        const isActive = activePreset === key
        return (
          <div
            key={key}
            tabIndex={0}
            role="button"
            aria-pressed={isActive}
            className={cn(
              "flex-1 min-w-[200px] p-3 rounded-xl border-2 transition-all cursor-pointer relative overflow-hidden group",
              getColorClasses(preset.color, isActive)
            )}
            onClick={() => handleSelect(key)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                handleSelect(key)
              }
            }}
          >
            {/* Left accent bar */}
            <div className={cn("absolute left-0 top-0 bottom-0 w-1", getBorderColor(preset.color))} />
            
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-white uppercase tracking-wider">{preset.label}</span>
              {isActive && <Check size={14} className={cn("text-white", preset.color === 'yellow' ? 'text-yellow-400' : preset.color === 'blue' ? 'text-blue-500' : 'text-green-500')} />}
            </div>

            <p className="text-xs text-gray-400 leading-tight mb-2 line-clamp-2">
              {preset.description}
            </p>

            <div className="text-xs font-mono text-gray-500 font-bold uppercase">
              WACC {(preset.values.wacc! * 100).toFixed(0)}% · 
              TGR {(preset.values.terminal_growth_rate! * 100).toFixed(0)}% · 
              Margin {(preset.values.ebit_margin! * 100).toFixed(0)}%
            </div>
          </div>
        )
      })}
    </div>
  )
}
