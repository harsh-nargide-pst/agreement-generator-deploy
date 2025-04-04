// Base OTP state interface with common properties
export interface BaseOtpState {
  otp: string;
  error: string;
  timer: number;
  isCountdownActive: boolean;
}

// OTP state interface for owner/authority/participant verification
export interface OtpState extends BaseOtpState {
  isVerified: boolean;
  isSent: boolean;
  showResendButton: boolean;
}

// OTP state interface for tenant verification
export interface TenantsOtpState {
  [key: number]: OtpState;
}

// Type for different user roles in OTP verification
export type OtpUserType =
  | "owner"
  | "tenant"
  | "authority"
  | "participants"
  | "witness";

// Response interface for OTP verification
export interface OTPVerificationResponse {
  success: boolean;
  type: OtpUserType;
  message: string;
}

export interface OTPInputProps {
  otpState: OtpState;
  onOtpChange: (value: string) => void;
  onSendOtp: () => void;
  onVerifyOtp: () => void;
  label?: string;
  disabledSendOtp?: boolean;
}

// Default OTP state
export const getDefaultOtpState = (): OtpState => ({
  otp: "",
  isVerified: false,
  isSent: false,
  error: "",
  timer: 0,
  isCountdownActive: false,
  showResendButton: false,
});

// Utility function to get updated OTP state on successful verification
export const getSuccessOtpState = (prevState: OtpState): OtpState => ({
  ...prevState,
  isVerified: true,
  isSent: false,
  otp: "",
  error: "",
  isCountdownActive: false,
  showResendButton: false,
});

// Utility function to get updated OTP state on verification failure
export const getFailureOtpState = (prevState: OtpState): OtpState => ({
  ...prevState,
  error: "Invalid OTP. Please enter the correct OTP.",
});
