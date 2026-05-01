"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AlertTriangle, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { apiFetch } from "@/lib/api"
import { useToast } from "@/components/ui/Toast"

interface DeletePortfolioModalProps {
  isOpen: boolean
  onClose: () => void
  portfolioId: string
  portfolioName: string
  onSuccess: () => void
}

export default function DeletePortfolioModal({ 
  isOpen, 
  onClose, 
  portfolioId, 
  portfolioName,
  onSuccess 
}: DeletePortfolioModalProps) {
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleDelete = async () => {
    setLoading(true)
    try {
      await apiFetch(`/users/me/portfolios/${portfolioId}`, {
        method: "DELETE",
      })
      toast({ type: "success", title: "Portfolio Deleted", description: `Portfolio "${portfolioName}" has been removed.` })
      onSuccess()
      onClose()
    } catch (err: any) {
      toast({ type: "error", title: "Delete Failed", description: err.message || "An error occurred." })
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
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="relative glass-panel w-full max-w-sm p-8 rounded-3xl bg-[#0d0d14] border border-red-500/20 shadow-2xl overflow-hidden text-center"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-red-500" />
            
            <div className="mx-auto w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-6">
              <AlertTriangle className="text-red-500" size={32} />
            </div>

            <h2 className="text-2xl font-bold text-white mb-2">Delete Portfolio?</h2>
            <p className="text-gray-400 text-sm mb-8">
              Are you sure you want to delete <span className="text-white font-bold">"{portfolioName}"</span>? 
              This will permanently remove all holdings and transaction history.
            </p>

            <div className="flex gap-3">
              <Button
                variant="ghost"
                onClick={onClose}
                className="flex-1 h-12 font-bold text-gray-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button
                onClick={handleDelete}
                disabled={loading}
                className="flex-1 h-12 bg-red-600 hover:bg-red-700 text-white font-bold"
              >
                {loading ? "Deleting..." : "Delete"}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
