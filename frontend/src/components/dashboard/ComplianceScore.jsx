/**
 * Compliance Score Widget - مؤشر درجة الامتثال
 * Circular progress indicator for compliance scores
 */
import React from 'react';

const getScoreColor = (score) => {
  if (score >= 90) return { class: 'text-green-400', stroke: '#22c55e', bg: 'bg-green-500/10' };
  if (score >= 70) return { class: 'text-yellow-400', stroke: '#eab308', bg: 'bg-yellow-500/10' };
  if (score >= 50) return { class: 'text-orange-400', stroke: '#f97316', bg: 'bg-orange-500/10' };
  return { class: 'text-red-400', stroke: '#ef4444', bg: 'bg-red-500/10' };
};

const getScoreLabel = (score) => {
  if (score >= 90) return { ar: 'ممتاز', en: 'Excellent' };
  if (score >= 70) return { ar: 'جيد', en: 'Good' };
  if (score >= 50) return { ar: 'يحتاج تحسين', en: 'Needs Improvement' };
  return { ar: 'حرج', en: 'Critical' };
};

export const ComplianceScoreCard = ({ 
  score = 0, 
  title_ar, 
  title_en, 
  subtitle_ar,
  icon: Icon,
  trend,
  size = 'default' 
}) => {
  const { class: colorClass, stroke, bg } = getScoreColor(score);
  const label = getScoreLabel(score);
  
  const circleSize = size === 'large' ? 120 : 80;
  const strokeWidth = size === 'large' ? 8 : 6;
  const radius = (circleSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = ((100 - score) / 100) * circumference;

  return (
    <div className={`finai-card ${bg} border-0`} data-testid={`score-card-${title_en?.toLowerCase().replace(' ', '-')}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {Icon && <Icon className={`w-5 h-5 ${colorClass}`} />}
            <h3 className="text-sm font-medium text-muted-foreground">{title_ar}</h3>
          </div>
          
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold number ${colorClass}`}>{score}%</span>
            {trend && (
              <span className={`text-sm ${trend > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {trend > 0 ? '↑' : '↓'} <span className="number">{Math.abs(trend)}%</span>
              </span>
            )}
          </div>
          
          <div className={`text-xs mt-1 ${colorClass}`}>{label.ar}</div>
          {subtitle_ar && (
            <div className="text-xs text-muted-foreground mt-2">{subtitle_ar}</div>
          )}
        </div>

        {/* Circular Progress */}
        <div className="score-circle" style={{ width: circleSize, height: circleSize }}>
          <svg width={circleSize} height={circleSize}>
            {/* Background Circle */}
            <circle
              cx={circleSize / 2}
              cy={circleSize / 2}
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              className="text-secondary"
            />
            {/* Progress Circle */}
            <circle
              cx={circleSize / 2}
              cy={circleSize / 2}
              r={radius}
              fill="none"
              stroke={stroke}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={progress}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-lg font-bold number ${colorClass}`}>{score}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Simple progress bar variant
export const ComplianceProgressBar = ({ score, label_ar, size = 'default' }) => {
  const { class: colorClass } = getScoreColor(score);
  const heightClass = size === 'small' ? 'h-1.5' : 'h-2';
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label_ar}</span>
        <span className={`number font-medium ${colorClass}`}>{score}%</span>
      </div>
      <div className={`compliance-progress ${heightClass}`}>
        <div 
          className={`compliance-progress-bar ${
            score >= 90 ? 'excellent' : 
            score >= 70 ? 'good' : 
            score >= 50 ? 'needs-improvement' : 'critical'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
};

export default ComplianceScoreCard;
