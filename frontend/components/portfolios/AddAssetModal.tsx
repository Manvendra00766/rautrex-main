"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { apiFetch } from "@/lib/api"
import { useToast } from "@/components/ui/Toast"

interface AddAssetModalProps {
  isOpen: boolean
  onClose: () => void
  portfolioId: string
  onSuccess: () => void
}

const ASSET_TYPES = ["Stock", "ETF", "Crypto", "Option"]

export default function AddAssetModal({ isOpen, onClose, portfolioId, onSuccess }: AddAssetModalProps) {
  const [ticker, setTicker] = useState("")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const [assetType, setAssetType] = useState("Stock")
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleAddAsset = async () => {
    if (!ticker || !quantity || !price) {
      toast({ type: "warning", title: "Missing fields", description: "Please fill in all required fields." })
      return
    }

    setLoading(true)
    try {
      await apiFetch(`/users/me/portfolios/${portfolioId}/positions`, {
        method: "POST",
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          quantity: Number(quantity),
          avg_cost: Number(price),
          asset_type: assetType,
        }),
      })
      toast({ type: "success", title: "Asset Added", description: `${ticker} has been added to your portfolio.` })
      onSuccess()
      onClose()
      // Reset form
      setTicker("")
      setQuantity("")
      setPrice("")
      setAssetType("Stock")
    } catch (err: any) {
      toast({ type: "error", title: "Failed to add asset", description: err.message || "An error occurred." })
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            className="relative glass-panel w-full max-w-md p-8 rounded-3xl bg-[#0d0d14] border border-white/10 shadow-2xl overflow-hidden"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent to-accent-foreground opacity-50" />
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>

            <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
              <Plus className="text-accent" size={24} /> Add Asset
            </h2>
            <p className="text-gray-500 text-sm mb-6">Enter details to add a new position to your portfolio.</p>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Ticker Symbol</Label>
                <Input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="AAPL, BTC, etc."
                  className="bg-surface h-12 border-white/5 focus:border-accent/50 transition-all font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Quantity</Label>
                  <Input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="0.00"
                    className="bg-surface h-12 border-white/5 focus:border-accent/50 transition-all font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Buy Price</Label>
                  <Input
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="0.00"
                    className="bg-surface h-12 border-white/5 focus:border-accent/50 transition-all font-mono"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Asset Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {ASSET_TYPES.map((type) => (
                    <button
                      key={type}
                      onClick={() => setAssetType(type)}
                      className={`px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
                        assetType === type
                          ? "bg-accent/10 border-accent text-white"
                          : "bg-surface border-white/5 text-gray-500 hover:text-gray-300"
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  className="flex-1 h-12 font-bold text-gray-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleAddAsset}
                  disabled={loading}
                  className="flex-1 h-12 bg-accent hover:bg-accent/90 text-black font-bold shadow-lg shadow-accent/20"
                >
                  {loading ? "Adding..." : "Add Asset"}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
