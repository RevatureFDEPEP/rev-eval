/**
 * NumberInput Component
 *
 * A styled number input with increment/decrement stepper buttons
 */

import * as React from 'react';
import { Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

export interface NumberInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  value?: number;
  onChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  className?: string;
}

const NumberInput = React.forwardRef<HTMLInputElement, NumberInputProps>(
  (
    {
      value = 0,
      onChange,
      min = 0,
      max = Infinity,
      step = 1,
      disabled = false,
      className,
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = React.useState<number>(value);

    // Sync internal value with prop value
    React.useEffect(() => {
      setInternalValue(value);
    }, [value]);

    const clampValue = (val: number): number => {
      return Math.max(min, Math.min(max, val));
    };

    const handleIncrement = () => {
      if (disabled) return;
      const newValue = clampValue(internalValue + step);
      setInternalValue(newValue);
      onChange?.(newValue);
    };

    const handleDecrement = () => {
      if (disabled) return;
      const newValue = clampValue(internalValue - step);
      setInternalValue(newValue);
      onChange?.(newValue);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      if (val === '' || val === '-') {
        setInternalValue(min);
        onChange?.(min);
        return;
      }

      const parsed = parseInt(val, 10);
      if (!isNaN(parsed)) {
        const clamped = clampValue(parsed);
        setInternalValue(clamped);
        onChange?.(clamped);
      }
    };

    const handleBlur = () => {
      // Ensure value is clamped on blur
      const clamped = clampValue(internalValue);
      if (clamped !== internalValue) {
        setInternalValue(clamped);
        onChange?.(clamped);
      }
    };

    const isMinDisabled = disabled || internalValue <= min;
    const isMaxDisabled = disabled || internalValue >= max;

    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={handleDecrement}
          disabled={isMinDisabled}
          tabIndex={-1}
        >
          <Minus className="h-4 w-4" />
          <span className="sr-only">Decrease</span>
        </Button>

        <input
          ref={ref}
          type="number"
          value={internalValue}
          onChange={handleInputChange}
          onBlur={handleBlur}
          disabled={disabled}
          min={min}
          max={max}
          step={step}
          className={cn(
            'flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-center text-sm shadow-sm transition-colors',
            'file:border-0 file:bg-transparent file:text-sm file:font-medium',
            'placeholder:text-slate-500',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950',
            'disabled:cursor-not-allowed disabled:opacity-50',
            // Hide spinners
            '[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none'
          )}
          {...props}
        />

        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={handleIncrement}
          disabled={isMaxDisabled}
          tabIndex={-1}
        >
          <Plus className="h-4 w-4" />
          <span className="sr-only">Increase</span>
        </Button>
      </div>
    );
  }
);

NumberInput.displayName = 'NumberInput';

export { NumberInput };
