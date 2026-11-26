# Metrics

None of the time daemons export Prometheus metrics, so two scripts read them every 30 s and write node_exporter textfiles into `/var/lib/prometheus/node-exporter` (`o11y_textfile_dir`). Alloy's embedded node_exporter ships them to the homelab Mimir tenant (datasource `mimir-homelab`), labelled `instance="<host>:9100"`. Every query is read-only; a source that fails writes only its `..._up 0`, so stale numbers disappear instead of lingering.

## On the clients: `time-client-metrics`

[`modules/time-sync/files/time-client-metrics`](https://github.com/SpechtLabs/homelab/blob/main/modules/time-sync/files/time-client-metrics), file `time_client.prom`.

| Metric | Meaning |
|--------|---------|
| `chrony_tracking_info{reference, refid}` | the source chrony follows; `reference="PTP"` for the PHC, `none` when unsynchronised |
| `chrony_tracking_system_offset_seconds` | system clock minus true time, as chrony estimates it (positive: fast). The alert and SLO metric |
| `chrony_tracking_last_offset_seconds`, `..._rms_offset_seconds` | last measured offset; long-term RMS |
| `chrony_tracking_frequency_ppm`, `..._residual_frequency_ppm`, `..._skew_ppm` | frequency correction and its error |
| `chrony_tracking_root_delay_seconds`, `..._root_dispersion_seconds` | path to the stratum 1 and the error accumulated |
| `chrony_tracking_stratum`, `..._update_interval_seconds` | |
| `chrony_tracking_leap_normal` | 1 while synchronised with no leap second pending |
| `ptp4l_master_offset_seconds` | PTP clients: NIC clock minus the grandmaster |
| `ptp4l_mean_path_delay_seconds` | PTP clients: one-way delay to timepi |
| `ptp4l_port_slave` | PTP clients: 1 while SLAVE; 0 when not, when `pmc` gets no answer, and when ptp4l isn't running (always written on PTP clients since 2026-11-27, so a dead ptp4l fires an alert instead of turning into no data) |
| `ptp4l_service_active` | PTP clients: 1 while `ptp4l@<interface>` is active |
| `ptp4l_gm_present` | PTP clients: 1 while a grandmaster is visible |
| `time_client_metrics_up{source}`, source `chrony` or `ptp4l` | 1 if the daemon answered; the `ptp4l` series exists only while `ptp4l@<interface>` is active |

## On timepi: `time-metrics`

[`modules/ptp-server/files/time-metrics.py`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/files/time-metrics.py), one file per source: `ntpsec.prom`, `gpsd.prom`, `pps.prom`, `ptp.prom`. Each has `time_metrics_up{source}`, `time_metrics_duration_seconds{source}` and `time_metrics_last_run_timestamp_seconds{source}`.

**ntpsec** (system variables, every association, counters, clients):

| Metric | Meaning |
|--------|---------|
| `ntpsec_stratum` | 1 on PPS, 2 on PTB, 16 unsynchronised. Alert `timepi — not synchronised` |
| `ntpsec_peer_selection{peer, kind}` | 0 reject ... 6 sys.peer, 7 pps.peer. `peer="PPS"` is the alert `timepi — GPS PPS lost` and the stratum-1 SLO |
| `ntpsec_sys_peer_info{peer}` | the system peer |
| `ntpsec_offset_seconds`, `ntpsec_system_jitter_seconds`, `ntpsec_clock_jitter_seconds` | combined offset and jitter |
| `ntpsec_root_delay_seconds`, `..._root_dispersion_seconds`, `..._root_distance_seconds` | the error bound clients see |
| `ntpsec_frequency_ppm`, `ntpsec_clock_wander_ppm`, `ntpsec_time_constant` | discipline |
| `ntpsec_leap`, `ntpsec_tai_offset_seconds`, `ntpsec_leapfile_expiry_timestamp_seconds` | leap state and the leap file's expiry |
| `ntpsec_peer_reach`, `..._reach_ratio`, `..._offset_seconds`, `..._delay_seconds`, `..._jitter_seconds`, `..._last_receive_age_seconds` | per association |
| `ntpsec_clients`, `ntpsec_client_requests`, `ntpsec_client_mean_interval_seconds` | from the MRU list |
| `ntpsec_packets_*_total`, `ntpsec_kod_sent_total`, `ntpsec_mru_*` | counters |

**gpsd**: `gpsd_fix_mode` (1 none, 2 2D, 3 3D), `gpsd_status`, `gpsd_satellites_visible`, `gpsd_satellites_used`, `gpsd_satellite_snr_dbhz{...}` and the other per-satellite series, `gpsd_dop`, `gpsd_pps_offset_seconds`, `gpsd_pps_pulses`, `gpsd_nmea_offset_seconds`, `gpsd_time_error_seconds`. `gpsd_observer_latitude_degrees` and `..._longitude_degrees` carry timepi's position: fine in Mimir, never in git.

**pps**: `pps_assert_total`, `pps_assert_timestamp_seconds`, `pps_assert_offset_seconds` from sysfs.

**ptp**: `ptp4l_port_state` (6 MASTER, 9 SLAVE, 2 FAULTY), `ptp4l_clock_class`, `ptp4l_clock_accuracy`, `ptp4l_time_source`, `ptp4l_utc_offset_seconds`, `ptp4l_utc_offset_valid`, `ptp4l_time_traceable`, `ptp4l_messages_total{direction, type}`, and from phc2sys's journal over the last 60 s: `phc2sys_offset_seconds`, `phc2sys_offset_abs_max_seconds`, `phc2sys_offset_rms_seconds`, `phc2sys_servo_state` (2 locked), `phc2sys_frequency_ppb`.

Full help text for every series is in the `# HELP` lines of the `.prom` files on the host.
