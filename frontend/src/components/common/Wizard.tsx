import React from 'react';
import { Check, ChevronRight, ChevronLeft, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface WizardStep {
  id: string | number;
  title: string;
  subtitle?: string;
  description?: string;
}

interface WizardProps {
  steps: WizardStep[];
  currentStep: number;
  onStepChange?: (step: number) => void;
  onNext?: () => void;
  onBack?: () => void;
  onFinish?: () => void;
  isNextDisabled?: boolean;
  isNextLoading?: boolean;
  nextLabel?: string;
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
}

export const Wizard: React.FC<WizardProps> = ({
  steps,
  currentStep,
  onStepChange,
  onNext,
  onBack,
  onFinish,
  isNextDisabled = false,
  isNextLoading = false,
  nextLabel,
  children,
  title,
  subtitle,
}) => {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="flex flex-col lg:flex-row gap-6 items-start max-w-7xl mx-auto w-full">
      {/* 1. Left Stepper Rail */}
      <div className="w-full lg:w-[280px] bg-white rounded-2xl border border-slate-200/90 shadow-card p-5 flex-shrink-0">
        <div className="mb-5 pb-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">
            {title || 'Configuration Wizard'}
          </h3>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>

        <nav aria-label="Progress" className="space-y-4">
          {steps.map((step, idx) => {
            const isCompleted = idx < currentStep;
            const isCurrent = idx === currentStep;

            return (
              <div
                key={step.id}
                onClick={() => {
                  if (isCompleted && onStepChange) onStepChange(idx);
                }}
                className={`flex items-start gap-3 p-2 rounded-xl transition-all ${
                  isCurrent
                    ? 'bg-brand-50/80 border border-brand-200/80'
                    : isCompleted
                    ? 'cursor-pointer hover:bg-slate-50'
                    : 'opacity-60'
                }`}
              >
                {/* Step Circle */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                    isCompleted
                      ? 'bg-emerald-600 text-white'
                      : isCurrent
                      ? 'bg-brand-600 text-white shadow-xs ring-4 ring-brand-100'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {isCompleted ? <Check className="w-4 h-4 stroke-[3]" /> : idx + 1}
                </div>

                {/* Step Metadata */}
                <div className="min-w-0">
                  <p
                    className={`text-xs font-bold truncate ${
                      isCurrent
                        ? 'text-brand-900'
                        : isCompleted
                        ? 'text-slate-800'
                        : 'text-slate-500'
                    }`}
                  >
                    {step.title}
                  </p>
                  {step.subtitle && (
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">
                      {step.subtitle}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      {/* 2. Main Form Card */}
      <div className="flex-1 w-full bg-white rounded-2xl border border-slate-200/90 shadow-card flex flex-col min-h-[560px] overflow-hidden">
        {/* Form Card Header */}
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-brand-600">
              Step {currentStep + 1} of {steps.length}
            </span>
            <h2 className="text-base font-bold text-slate-900 mt-0.5">
              {steps[currentStep]?.title}
            </h2>
          </div>
          {steps[currentStep]?.description && (
            <p className="text-xs text-slate-500 max-w-sm text-right hidden sm:block">
              {steps[currentStep].description}
            </p>
          )}
        </div>

        {/* Form Card Body */}
        <div className="p-6 flex-1 flex flex-col overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.18 }}
              className="flex-1 flex flex-col"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Form Card Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-white flex items-center justify-between gap-3">
          <button
            onClick={onBack}
            disabled={isFirstStep}
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl border border-slate-200 transition-colors ${
              isFirstStep
                ? 'opacity-40 cursor-not-allowed bg-slate-50 text-slate-400'
                : 'bg-white hover:bg-slate-50 text-slate-700'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Back</span>
          </button>

          <button
            onClick={isLastStep ? onFinish : onNext}
            disabled={isNextDisabled || isNextLoading}
            className={`inline-flex items-center gap-1.5 px-5 py-2.5 text-xs font-bold rounded-xl shadow-xs transition-all ${
              isNextDisabled || isNextLoading
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-brand-600 hover:bg-brand-700 text-white shadow-brand-500/20'
            }`}
          >
            <span>
              {isNextLoading
                ? 'Processing...'
                : nextLabel || (isLastStep ? 'Confirm & Finish' : 'Next Step')}
            </span>
            {!isNextLoading && (isLastStep ? <Check className="w-4 h-4 stroke-[2.5]" /> : <ChevronRight className="w-4 h-4 stroke-[2.5]" />)}
          </button>
        </div>
      </div>
    </div>
  );
};
