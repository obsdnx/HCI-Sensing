"""
Madgwick AHRS filter — IMU-only (accel + gyro, no magnetometer).
Pure Python so it runs on MicroPython without numpy.
"""
import math


class MadgwickAHRS:
    def __init__(self, beta=0.1, sample_period=0.01):
        self.beta = beta
        self.dt = sample_period
        self.q = [1.0, 0.0, 0.0, 0.0]

    def update(self, gx, gy, gz, ax, ay, az):
        """gyro in °/s, accel in g."""
        # Convert gyro to rad/s
        gx = math.radians(gx)
        gy = math.radians(gy)
        gz = math.radians(gz)

        q0, q1, q2, q3 = self.q

        norm = math.sqrt(ax*ax + ay*ay + az*az)
        if norm < 1e-10:
            return
        ax /= norm; ay /= norm; az /= norm

        _2q0 = 2*q0; _2q1 = 2*q1; _2q2 = 2*q2; _2q3 = 2*q3
        _4q0 = 4*q0; _4q1 = 4*q1; _4q2 = 4*q2
        _8q1 = 8*q1; _8q2 = 8*q2
        q0q0 = q0*q0; q1q1 = q1*q1; q2q2 = q2*q2; q3q3 = q3*q3

        s0 = _4q0*q2q2 + _2q2*ax + _4q0*q1q1 - _2q1*ay
        s1 = _4q1*q3q3 - _2q3*ax + 4*q0q0*q1 - _2q0*ay - _4q1 + _8q1*q1q1 + _8q1*q2q2 + _4q1*az
        s2 = 4*q0q0*q2 + _2q0*ax + _4q2*q3q3 - _2q3*ay - _4q2 + _8q2*q1q1 + _8q2*q2q2 + _4q2*az
        s3 = 4*q1q1*q3 - _2q1*ax + 4*q2q2*q3 - _2q2*ay

        norm_s = math.sqrt(s0*s0 + s1*s1 + s2*s2 + s3*s3)
        if norm_s > 0:
            s0 /= norm_s; s1 /= norm_s; s2 /= norm_s; s3 /= norm_s

        qDot0 = 0.5*(-q1*gx - q2*gy - q3*gz) - self.beta*s0
        qDot1 = 0.5*( q0*gx + q2*gz - q3*gy) - self.beta*s1
        qDot2 = 0.5*( q0*gy - q1*gz + q3*gx) - self.beta*s2
        qDot3 = 0.5*( q0*gz + q1*gy - q2*gx) - self.beta*s3

        q0 += qDot0 * self.dt
        q1 += qDot1 * self.dt
        q2 += qDot2 * self.dt
        q3 += qDot3 * self.dt

        norm = math.sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        self.q = [q0/norm, q1/norm, q2/norm, q3/norm]

    def euler(self):
        """Returns (roll, pitch, yaw) in degrees."""
        q0, q1, q2, q3 = self.q
        roll  = math.degrees(math.atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1*q1 + q2*q2)))
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2*(q0*q2 - q3*q1)))))
        yaw   = math.degrees(math.atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2*q2 + q3*q3)))
        return roll, pitch, yaw
