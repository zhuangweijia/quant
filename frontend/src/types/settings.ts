export interface BrokerConfig {
  broker_name: string;
  market: string;
  api_key: string;
  has_secret: boolean;
  params: Record<string, any>;
  connected: boolean;
}

export interface NotificationConfig {
  email_enabled: boolean;
  email_smtp_host: string;
  email_smtp_port: number;
  email_sender: string;
  has_email_password: boolean;
  email_use_ssl: boolean;
  email_recipient: string;
  webhook_enabled: boolean;
  webhook_url: string;
  has_webhook_secret: boolean;
  notify_levels: string[];
}

export interface SystemParams {
  [key: string]: string;
}

export interface TradingModeConfig {
  mode: string;
}

export interface ProfileInfo {
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface PasswordChangeRequest {
  old_password: string;
  new_password: string;
  confirm_password: string;
}
