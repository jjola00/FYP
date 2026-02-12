"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API_BASE } from "@/lib/api";

type Status = "idle" | "sending" | "sent" | "error";

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [device, setDevice] = useState("");
  const [message, setMessage] = useState("");
  const [images, setImages] = useState<File[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetForm = () => {
    setName("");
    setCategory("");
    setDevice("");
    setMessage("");
    setImages([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 3) {
      alert("Max 3 images allowed");
      e.target.value = "";
      return;
    }
    setImages(files);
  };

  const handleRemoveImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async () => {
    if (!category || !device) return;
    if (!message.trim()) return;

    setStatus("sending");

    const formData = new FormData();
    formData.append("message", message.trim());
    formData.append("category", category);
    formData.append("device", device);
    if (name.trim()) formData.append("name", name.trim());
    images.forEach((img) => formData.append("images", img));

    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to send");
      setStatus("sent");
      resetForm();
      setTimeout(() => {
        setStatus("idle");
        setOpen(false);
      }, 2000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Toggle button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105"
          aria-label="Open feedback form"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      )}

      {/* Feedback panel */}
      {open && (
        <div className="w-80 rounded-lg border bg-background p-4 shadow-xl">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Send Feedback</h3>
            <button
              onClick={() => setOpen(false)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Close feedback form"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div className="flex flex-col gap-3">
            <div>
              <Label htmlFor="fb-name" className="text-xs text-muted-foreground">
                Name (optional)
              </Label>
              <Input
                id="fb-name"
                placeholder="Anonymous"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 h-8 text-sm"
              />
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">
                Related to
              </Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="mt-1 h-8 text-sm">
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="line">Line Captcha</SelectItem>
                  <SelectItem value="image">Image Captcha</SelectItem>
                  <SelectItem value="both">Both / General</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">
                Device
              </Label>
              <Select value={device} onValueChange={setDevice}>
                <SelectTrigger className="mt-1 h-8 text-sm">
                  <SelectValue placeholder="What are you using?" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="phone">Phone</SelectItem>
                  <SelectItem value="laptop">Laptop</SelectItem>
                  <SelectItem value="tablet">Tablet / iPad</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="fb-message" className="text-xs text-muted-foreground">
                Message
              </Label>
              <Textarea
                id="fb-message"
                placeholder="What's on your mind?"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="mt-1 min-h-[80px] text-sm"
                maxLength={2000}
              />
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">
                Screenshots (max 3)
              </Label>
              <Input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageChange}
                className="mt-1 h-8 text-xs"
              />
              {images.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {images.map((img, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs"
                    >
                      {img.name.length > 15
                        ? img.name.slice(0, 12) + "..."
                        : img.name}
                      <button
                        onClick={() => handleRemoveImage(i)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        x
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <Button
              size="sm"
              onClick={handleSubmit}
              disabled={!category || !device || !message.trim() || status === "sending"}
              className="w-full"
            >
              {status === "sending"
                ? "Sending..."
                : status === "sent"
                  ? "Sent! Thank you"
                  : status === "error"
                    ? "Failed - try again"
                    : "Send Feedback"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
